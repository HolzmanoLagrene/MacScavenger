from scp import SCPClient
from paramiko import SSHClient
from pssh.clients.native.parallel import ParallelSSHClient


hosts = {'9f8': '192.168.3.3'}
interface = 'wlan0'


ssh = SSHClient()
ssh.load_system_host_keys()
for k, v in hosts.items():
    ssh.connect(v, username='root', password='holz')
    with SCPClient(ssh.get_transport()) as scp:
        scp.put('MacScavengerMonitor.py', '/root/macscav/monitor.py')


client = ParallelSSHClient(hosts.values(), user='root', password='holz')
output = client.run_command('python3 ./macscav/monitor.py 9f8 0.0.0.0 9999')
