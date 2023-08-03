import os

hostname = "192.168.1.1"
counter = 0

for i in range(10):
    response = os.system("ping -c 1 " + hostname)

    if response == 0:
        print(f"{hostname} is up!")
        counter += 1
    else:
        print(f"{hostname} is down!")


if counter < 9:
    os.system('systemctl reboot -i')