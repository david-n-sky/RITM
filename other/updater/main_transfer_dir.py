import paramiko
import os

source_folder = 'путь к отправляемому файлу'
destination_folder = 'путь к директории, где будет лежать файл + его название'
username = 'root'
password = 'qscfthm'


def transfer_folder(ip, username, password, source_dir, destination_dir):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(ip, username=username, password=password)

    command = f'mkdir -p {destination_dir}'  # create new folder, if it's not exist
    ssh_client.exec_command(command)

    try:
        sftp_client = ssh_client.open_sftp()

        for root, dirs, files in os.walk(source_dir):
            for file in files:
                local_path = os.path.join(root, file)
                lp = local_path.replace(source_dir, '')
                remote_path = os.path.join(destination_dir)
                sftp_client.put(local_path, remote_path + lp)

        sftp_client.close()

        print(f'The file {source_dir} was successfully uploaded to {ip}')
    except Exception as e:
        print(f'Error {e} occurred on ip {ip}')


with open("ip.txt", 'r') as f:  # get a list of ip
    ip_addresses = f.read().splitlines()

for ip in ip_addresses:
    transfer_folder(ip, username, password, source_folder, destination_folder)