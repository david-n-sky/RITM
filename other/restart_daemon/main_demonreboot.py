import os


with open("ip.txt", 'r') as f:  # get a list of ip
    ip_addresses = f.read().splitlines()

for ip in ip_addresses:
    os.system ("sshpass -p \"qscfthm\" ssh root@%s \"chmod +x /home/work_scripts/restart_daemon.sh && sed -i -e 's/\r$//' /home/work_scripts/restart_daemon.sh && /home/work_scripts/restart_daemon.sh\"" % (ip)) 
    
