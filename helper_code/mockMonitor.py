import hashlib
import json
import socketserver
import sys
import time
from collections import deque

from streamz import Stream, glob

pid = 9999
capture = deque(maxlen=1)


class MacScavengerTCPHandler(socketserver.BaseRequestHandler):

    def pack_data(self, data_in):

        return json.loads(data_in)

    def transmit_stream(self, data):
        self.request.sendall(json.dumps(data).encode())

    def start_monitor(self):
        source = Stream()
        source.map(self.pack_data).partition(50).sink(self.transmit_stream)
        capture.append(True)
        print('Data Stream Started!')
        for fn in glob('mockData/{}/*.json'.format(datapath)):
            while capture[0]:
                source.emit(fn)
        print('Data Stream stopped')

    def stop_monitor(self):
        try:
            print('Stopping Monitor')
            capture.append(False)
            self.request.sendall('0'.encode())
        except Exception as e:
            self.request.sendall('1'.encode())
            print('Stopping to monitor failed! - Reason: {}'.format(e))

    def handle(self):
        data = str(self.request.recv(1024).strip(), 'utf-8')
        if data == 'setup_ap':
            print('Successfully Setup Monitoring Device')
            self.request.sendall('0'.encode())
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
            name, host, port, datapath = sys.argv[1], '0.0.0.0', int(sys.argv[2]), sys.argv[3]
            server = socketserver.ThreadingTCPServer((host, port), MacScavengerTCPHandler)
            print('Server Up and Running!')
            server.serve_forever()
            no_success = False
        except:
            print('Port still blocked ...waiting a couple of seconds ... ')
            time.sleep(5)
