import hashlib
import json
import socketserver
import subprocess
import sys
import time
from collections import deque
from pathlib import Path
from threading import Thread

import psutil
import pyric.pyw as pyw
from streamz import Stream

pid = 9999
capture = deque(maxlen=1)


class MacScavengerTCPHandler(socketserver.BaseRequestHandler):

    def pack_data(self, data_in):
        data = json.loads(data_in)
        epoch = data['layers']['frame']['frame_frame_time_epoch']
        rssi = data['layers']['radiotap']['radiotap_radiotap_dbm_antsignal']
        ssid = data['layers']['wlan'][0]['wlan_wlan_ta']
        ie = data['layers']['wlan'][1]
        result = {'ap': name,
                  'epoch': float(epoch) * 10e9,
                  'rssi': int(rssi),
                  'ie': hashlib.md5(json.dumps(ie, sort_keys=True).encode()).hexdigest(),
                  'ssid': ssid
                  }
        return result

    def switch_channel_loop(self, capture):
        mon0 = pyw.getcard('mon0')
        channel_range = [1, 3, 5, 7, 9, 11, 13]
        i = 0
        while capture[0]:
            s = 'Listening on channel {}'.format(channel_range[i])
            print('\033[1A{}\033[K'.format(s))
            pyw.chset(mon0, channel_range[i], None)
            time.sleep(0.25)
            i = (i + 1) % len(channel_range)

    def setup_ap(self):

        if 'mon0' in pyw.winterfaces():
            mon0 = pyw.getcard('mon0')
            if pyw.modeget(mon0) == 'monitor':
                try:
                    pyw.up(mon0)
                    pyw.chset(mon0, 1, None)
                    success = True
                except Exception as e:
                    success = False
            else:
                try:
                    pyw.down(mon0)
                    pyw.modeset(mon0, 'monitor')
                    pyw.up(mon0)
                    pyw.chset(mon0, 1, None)
                    success = True
                except Exception as e:
                    success = False
        else:
            card_name = ''
            for interface in pyw.winterfaces():
                if interface.startswith('wlx7'):
                    card_name = interface
                    break
            c0 = pyw.getcard(card_name)
            if 'monitor' in pyw.devmodes(c0):
                try:
                    pyw.down(c0)
                    pyw.modeset(c0, 'monitor')
                    pyw.up(c0)
                    mon0 = pyw.devset(c0, 'mon0')
                    pyw.up(mon0)
                    pyw.chset(mon0, 1, None)
                    success = True
                except Exception as e:
                    success = False
            else:
                success = False

        if success:
            print('Successfully Setup Monitoring Device')
            self.request.sendall('0'.encode())
        else:
            print('Error Setting up Monitoring Device')
            self.request.sendall('1'.encode())

    def transmit_stream(self, data):
        self.request.sendall(json.dumps(data).encode())

    def store_local(self, data):
        if len(data) > 0:
            from_ = min([data_['epoch'] for data_ in data])
            to_ = max([data_['epoch'] for data_ in data])
            Path('./json_data').mkdir(parents=True, exist_ok=True)
            with open('./json_data/{0}-{1}.json'.format(from_, to_), 'w+') as out_:
                json.dump(data, out_)
        else:
            pass

    def start_monitor(self):
        command_1 = ['tshark',
                     '-i',
                     'mon0',
                     '-Q',
                     '-l',
                     '-T',
                     'ek',
                     'type mgt subtype probe-req'
                     ]

        capture.append(True)
        channel_switch_thread = Thread(target=self.switch_channel_loop, args=(capture,))
        channel_switch_thread.start()

        process = subprocess.Popen(command_1, stdout=subprocess.PIPE, universal_newlines=True)
        global pid
        pid = process.pid
        source = Stream()
        if storage == 'local':
            print('Local Storage')
            source.map(self.pack_data).partition(50).sink(self.store_local)
        else:
            source.map(self.pack_data).sink(self.transmit_stream)

        print('Data Stream Started!')
        while process.returncode is None and capture[0]:
            data = process.stdout.readline()
            if '"_type": "pcap_file"' in data:
                continue
            if not data:
                break
            try:
                source.emit(data)
            except BrokenPipeError as bp:
                break
        print('Data Stream stopped')

    def stop_monitor(self):
        try:
            print('Stopping Channel Switching')
            capture.append(False)
            print('Stopping pid')
            p = psutil.Process(pid)
            p.terminate()
            gone, alive = psutil.wait_procs([p], timeout=3, callback=lambda x: self.request.sendall('0'.encode()))
            for p in alive:
                p.kill()
                print('Just killed {}'.format(p))
        except Exception as e:
            self.request.sendall('1'.encode())
            print('Stopping to monitor failed! - Reason: {}'.format(e))

    def handle(self):
        data = str(self.request.recv(1024).strip(), 'utf-8')
        if data == 'setup_ap':
            self.setup_ap()
        elif data == 'start_monitor':
            self.start_monitor()
        elif data == 'stop_monitor':
            self.stop_monitor()
        else:
            self.request.sendall('Unknown command {}'.format(data).encode())


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


if __name__ == "__main__":
    no_success = True
    while no_success:
        try:
            name, host, port = sys.argv[1], '0.0.0.0', int(sys.argv[2])
            server = socketserver.ThreadingTCPServer((host, port), MacScavengerTCPHandler)
            print('Server Up and Running!')
            try:
                storage = sys.argv[3]
                print('Local Storage')
            except:
                storage = 'remote'
                print('Remote Storage')
            server.serve_forever()
            no_success = False
        except:
            print('Port still blocked ...waiting a couple of seconds ... ')
            time.sleep(5)
