import configparser
import os
isExe = False
config = configparser.ConfigParser()
config_path = f"{os.path.dirname(__file__)}\\config.ini"

# TODO : config reading
config.read(config_path,encoding='UTF-8')
