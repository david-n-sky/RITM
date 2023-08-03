import glob
import subprocess
import config
import log

VENDOR_ID_PREFIX = "E: ID_VENDOR_ID="


class Usb:
    def __init__(self):
        uhfVids = set()
        for vid in config.data['Uhf']['UsbVids'].split(' '):
            vid = vid.strip()
            if len(vid) > 0:
                uhfVids.add(vid)

        log.debug(f"UHF reader VIDs: {uhfVids}")

        self.uhfPorts = []

        ports = glob.glob('/dev/ttyUSB*')
        for port in ports:
            result = subprocess.run(['udevadm', 'info', port], stdout=subprocess.PIPE)
            out = result.stdout
            out = out.decode('utf-8')
            for line in out.split("\n"):
                line = line.strip()
                if line.startswith(VENDOR_ID_PREFIX):
                    vid = line[len(VENDOR_ID_PREFIX):]
                    if vid in uhfVids:
                        self.uhfPorts.append(port)

        log.debug(f"UHF reader ports: {self.uhfPorts}")

    def getUhfPorts(self):
        return self.uhfPorts
