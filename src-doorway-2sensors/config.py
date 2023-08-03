import sys
import configparser

CONFIG_FN = "main.cfg"

data = configparser.ConfigParser()

if len(data.read(CONFIG_FN, encoding='utf8')) != 1:
    print(f"Failed to read config file '{CONFIG_FN}'")
    sys.exit(1)