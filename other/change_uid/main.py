import xlrd
import os
import paramiko
import re


with open("ip.txt", 'r') as f:  # get a list of ip
    ip_addresses = f.read().splitlines()

# get data from xls table
workbook = xlrd.open_workbook('modules.xls')
sheet = workbook.sheet_by_index(0)  # num of the sheet

name_and_uuid = {}

for row_index in range(1, sheet.nrows):
    module_names = sheet.cell(row_index, 1).value  # 2 row
    uuids = sheet.cell(row_index, 4).value  # 5 row

    match = re.search(pattern=r'gf-011', string=module_names)
    if match:
        module_names = module_names[match.end():]

    name_and_uuid[module_names] = uuids


def uuid_change(ip):
    try:
        # check module name via ssh
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username='root', password='qscfthm')

        stdin, stdout, stderr = ssh.exec_command(f'cat /etc/hostname')
        hostname = stdout.read().decode('utf-8')
        hostname = hostname.strip()

        uuid = name_and_uuid[hostname]  # find the corresponding uuid in the dict

        with open('uuid.cfg', 'w', encoding='utf-8') as f:
            f.write(f'[Server]\n# ID модуля, передаваемое в запросах на сервер\nModule = {uuid}\n# {hostname}')

        sftp = ssh.open_sftp()
        sftp.put(os.getcwd() + '/uuid.cfg', '/home/work_scripts/uuid.cfg')

        ssh.close()
        del ssh, stdin, stdout, stderr

        print(f'The file uuid.cfg was successfully uploaded to {ip}')

    except Exception as e:
        print(f'An error occurred:{e}')


for ip in ip_addresses:
    uuid_change(ip)
