import sys
import configparser

CONFIG_FN = "main.cfg"
CONFIG_UUID = "uuid.cfg"

data = configparser.ConfigParser()
if len(data.read(CONFIG_FN, encoding='utf8')) != 1:
    print(f"Failed to read config file '{CONFIG_FN}'")
    sys.exit(1)

data_uuid = configparser.ConfigParser()
if len(data_uuid.read(CONFIG_UUID, encoding='utf8')) != 1:
    print(f"Failed to read config file '{CONFIG_UUID}'")
    sys.exit(1)
