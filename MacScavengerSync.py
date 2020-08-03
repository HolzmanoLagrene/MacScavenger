import ast
import re
import socket
import time
import warnings
from collections import deque
from threading import Thread

import termtables as tt
from streamz import Stream

warnings.filterwarnings("ignore")
#from SyncDataBaseInterfaces import AWS
from SyncDataBaseInterfaces import Local

class Swarm:
    def __init__(self):
        self.device_list = []
        self.threads = []
        self.streams = []
        self.last_stub = {}
        self.q = deque(maxlen=1)
        self.database = None
        #self.database = AWS.SyncDataBaseAWS()

    def setup_devices(self):
        for device in self.device_list:
            device.setup_ap()

    def remove_device(self, device):
        self.device_list.remove(device)

    def clear_devices(self):
        self.device_list = []

    def does_exist(self, device_name):
        for device in self.device_list:
            if device_name == device.name:
                return device
        return None

    def add_device(self, capture_device):
        self.device_list.append(capture_device)

    def prepare_swarm(self):
        for device in self.device_list:
            device.setup_ap()

    def save_swarm(self):
        result = []
        for device in self.device_list:
            result.append({'name': device.name, 'host': device.host, 'port': device.port})
        return result

    def load(self, devices):
        for device in devices:
            dev_ = CaptureDevice(device['name'], device['host'], device['port'])
            self.add_device(dev_)

    def put_together_stubs(self, new_data):
        rx = r'(\{[^{}]+\})'
        all_data = self.last_stub + str(new_data, 'utf-8')
        matches = re.findall(rx, all_data)
        rest_data = all_data
        for match in matches:
            rest_data = rest_data.replace(match, '')
        try:
            matches = [ast.literal_eval(match) for match in matches]
        except:
            print()
        self.last_stub = rest_data
        return matches

    def write_to_database(self, data):
        if len(data) > 0:
            self.database.write(data)
        else:
            pass

    def capture_and_fetch(self):
        if not self.database:
            self.database = Local.SyncDataBaseLocal()
        self.q.append(True)
        for device in self.device_list:
            source = Stream(asynchronous=False)
            thread = Thread(target=device.capture_and_fetch, args=(source, self.q,))
            thread.start()
            self.threads.append(thread)
        print('Connecting to Devices ...', end='')
        time.sleep(5)
        streams = []
        for device in self.device_list:
            streams.append(device.stream)

        if len(streams) == 1:
            streams[0].timed_window(20).sink(self.write_to_database)
        else:
            streams[0]. \
                union(*streams[1:]). \
                timed_window(20).sink(self.write_to_database)
        print(' Finished')

    def stop_capture(self):
        print('Stopping Devices ...', end='')
        self.q.append(False)
        for thread in self.threads:
            thread.join()
        for device in self.device_list:
            device.stop_process()
        print(' Finished')

    def get_swarm_overview(self):
        data = []
        for device in self.device_list:
            if device.retries == 0:
                dev_on_retr = device.online
            else:
                dev_on_retr = str(device.online) + '(Retries {})'.format(device.retries)
            data.append([device.name, device.host, device.port, device.set_up, dev_on_retr, device.monitoring, device.total_data_packets])
        if len(data) == 0:
            return None
        table = tt.to_string(
            data,
            header=["Name", "Host", "Port", "Setup", "Alive", "Monitoring", "Data Transmitted"],
            padding=(0, 1),
            alignment="ccccccc"
        )
        return table


class CaptureDevice:
    def __init__(self, name, address, port):
        self.name = name
        self.host = address
        self.port = port
        self.total_data_packets = 0
        self.last_stub = ''
        self.multipath_stub = []
        self.stream = None
        self.source = None

        self.set_up = False
        self.online = False
        self.monitoring = False
        self.retries = 0
        # self.setup_ap()

    def remove_multipath_fading(self, data):
        return data
        # total_data = data + self.multipath_stub
        # if len(total_data) <= 10:
        #     self.multipath_stub = total_data
        #     return []
        # else:
        #     self.multipath_stub = []
        #     x = [d['epoch'] for d in data]
        #     y = [d['rssi'] for d in data]
        #     threshold = lowess(y, x, is_sorted=False, frac=0.5, it=0)
        #     filtered = [y for f, y in zip(threshold[:, 1], data) if y['rssi'] >= f]
        #     return filtered

    def put_together_stubs(self, new_data):
        rx = r'(\{[^{}]+\})'
        all_data = self.last_stub + str(new_data, 'utf-8')
        matches = re.findall(rx, all_data)
        rest_data = all_data
        for match in matches:
            rest_data = rest_data.replace(match, '')
        parsed_matches = [ast.literal_eval(match) for match in matches]
        self.last_stub = rest_data
        return parsed_matches

    def register_data_packets(self, x):
        self.total_data_packets += len(x)
        return x

    def connect_device(self, run_on):
        while run_on[0]:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.connect((self.host, self.port))
                    self.retries = 0
                    sock.sendall(bytes('start_monitor', "utf-8"))
                    continue_ = run_on[0]
                    while continue_:
                        data = sock.recv(1024)
                        if not data:
                            self.monitoring = False
                            self.online = False
                            break
                        self.online = True
                        self.monitoring = True
                        self.source.emit(data)
                        continue_ = run_on[0]
                if run_on[0]:
                    pass
                else:
                    self.monitoring = True
                    break
            except Exception as e:
                self.retries += 1
                self.monitoring = False
                self.online = False
                pass

    def capture_and_fetch(self, source, run_on):
        self.stream = source. \
            map(lambda x: self.put_together_stubs(x)). \
            flatten(). \
            timed_window(1). \
            map(lambda x: self.remove_multipath_fading(x)). \
            map(lambda x: self.register_data_packets(x)). \
            flatten()

        self.source = source

        self.connect_device(run_on)

    def stop_process(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.host, self.port))
                sock.sendall(bytes('stop_monitor', "utf-8"))
                data = sock.recv(1024)
                received = str(data, "utf-8")
                if received == '0':
                    self.online = True
                    self.monitoring = False
                elif received == '1':
                    self.online = True
                    self.monitoring = True
        except Exception as e:
            self.online = False
            self.monitoring = False

    def setup_ap(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                sock.connect((self.host, self.port))
                sock.sendall(bytes('setup_ap', "utf-8"))
                data = sock.recv(1024)
                received = str(data, "utf-8")
                if received == '0':
                    self.online = True
                    self.set_up = True
                elif received == '1':
                    self.online = True
                    self.set_up = False
        except Exception as e:
            self.online = False
            self.set_up = False
