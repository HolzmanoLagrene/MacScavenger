import ast
import os
import time
from cmd import Cmd

import yaml

from MacScavengerAnalyzer import ScavengerAnalyzer
from MacScavengerSync import Swarm, CaptureDevice

try:
    import readline
except ImportError:
    readline = None


class ScavengerShell(Cmd):
    prompt = 'MacScavenger> '
    intro = "Welcome! Type ? to list commands"
    swarm = Swarm()
    histfile = './config/history'

    def preloop(self):
        if readline and os.path.exists(self.histfile):
            readline.read_history_file(self.histfile)

    def postloop(self):
        if readline:
            readline.set_history_length(1000)
            readline.write_history_file(self.histfile)

    def do_exit(self, inp):
        return True

    def do_load(self, inp):
        self.swarm.clear_devices()
        root, ext = os.path.splitext(inp)
        if not ext:
            path = root + '.yaml'
        else:
            path = root + ext
        try:
            with open('./config/' + path, 'r') as out_:
                devices = yaml.load(out_, Loader=yaml.FullLoader)
            self.swarm.load(devices)
            print('Loaded {} Devices'.format(len(devices)))
        except FileNotFoundError:
            print('No such file')

    def help_load(self):
        print('Specify the path to your configuration file.')

    def do_setup(self, inp):
        self.swarm.setup_devices()

    def help_exit(self):
        print('Leave MacScavenger Shell')

    def help_setup(self):
        print('Sets the network card of all monitor nodes to monitor mode')

    def do_save(self, inp):
        if inp == '':
            inp = 'config'
        root, ext = os.path.splitext(inp)
        path = root + '.yaml'
        with open('./config/' + path, 'w+') as out_:
            devices = self.swarm.save_swarm()
            yaml.dump(devices, out_)
        print('Saved {} Devices'.format(len(devices)))

    def help_save(self):
        print('Saves the list of used monitoring devices to a configuration file in specified path')

    def do_ls(self, inp):
        try:
            while True:
                table = self.swarm.get_swarm_overview()
                if table:
                    n = table.count('\n') + 2
                    print(table)
                    print('\033[{}A'.format(n))
                    time.sleep(1)
                else:
                    print('No devices registered')
                    break
        except KeyboardInterrupt:
            print('\033[{}B'.format(n))
            pass

    def help_ls(self):
        print('Prints detailed overview of the monitoring devices')

    def emptyline(self):
        pass

    def do_stop(self, inp):
        self.swarm.stop_capture()

    def help_stop(self):
        print('Stops the data gathering process')

    def do_start(self, inp):
        self.swarm.capture_and_fetch()

    def help_start(self):
        print('Starts the data gathering process')

    def do_add(self, inp):
        input_split = inp.split()
        if len(input_split) != 3:
            print("*** Wrong amount of arguments! Command must follow order: Name Host Port")
            return
        name = input_split[0]
        ip = input_split[1]
        port = input_split[2]
        try:
            port = int(port)
        except:
            print("*** {} is not a valid port".format(port))
            return

        device = CaptureDevice(name, ip, port)
        self.swarm.add_device(device)
        print('Added Device "{0}" on {1}:{2}'.format(name, ip, port))

    def help_add(self):
        print('Add a monitoring device by specifying name, ip and port')

    def do_clear(self, inp):
        self.swarm.clear_devices()

    def help_clear(self):
        print('Clears the list of monitoring devices')

    def do_rm(self, inp):
        success = self.swarm.does_exist(inp)
        if success:
            self.swarm.remove_device(success)
            print('Removed Device "{0}" on {1}:{2}'.format(success.name, success.host, success.port))
        else:
            print('No Device with name {} found'.format(inp))

    def help_rm(self):
        print('Removes a specified monitoring device from the list.')

    def do_analyze(self, inp):
        def are_ap_positions_valid(ap_positions):
            try:
                ast.literal_eval(ap_positions)
                return True
            except:
                pass

        def is_agreement_valid(agreement):
            return True

        ap_positions = None

        while ap_positions is None:
            ap_positions = input('Please enter Access Point Positons in the following form {"ap1":(0,0), "ap2":(5,0),"ap3":(5,5),"ap4":(0,5)}\n')
            if not are_ap_positions_valid(ap_positions):
                ap_positions = None
                print('Unknown Format - Please try again! \n')
        print()
        analyzer = ScavengerAnalyzer(ast.literal_eval(ap_positions))
        analyzer_config = analyzer.get_config()
        print('Analyzer has the following Configuration:')
        print('- Interval Size in seconds: {0}\n'
              '- Assumed Walking Speed in km/h: {1}\n'
              '- In Burst Time Threshold in seconds: {2}\n'
              '- Min. AP detection Rate: {3}\n'
              '- Verbosity: {4}'
              .format(*analyzer_config)
              )
        agreement = input('Do you agree with this configuration? Type y/n!')
        agreement = agreement.lower()
        if is_agreement_valid(agreement):
            if agreement == 'n':
                print('Yes you are!!')

        data_path = input('Please enter your data path\n')
        data_path = data_path + '/*.json'
        print('Starting Analysis ...')
        analyzer.start(data_path)
        analyzer.summary()

    def help_analyze(self):
        print('Start data analysis process.')


if __name__ == '__main__':
    ScavengerShell().cmdloop()

# {'tinkerboard1': (2, 0), 'tinkerboard2': (0, 2), 'tinkerboard3': (4, 2), 'tinkerboard4': (2, 4)}
