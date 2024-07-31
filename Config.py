import configparser
import os

config = configparser.ConfigParser()
config_path = './Assets/config.ini'
# TODO : config reading
config.read(config_path,encoding='UTF-8')
