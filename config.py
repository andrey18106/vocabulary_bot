# -*- coding: utf-8 -*-

from dotenv import load_dotenv
import os

ROOT_DIR = os.path.dirname(__file__)
env_path = ROOT_DIR + '/.env'
load_dotenv(dotenv_path=env_path)

TOKEN = os.getenv('TOKEN')
TOKEN_DEV = os.getenv('TOKEN_DEV')
DEV_ID = os.getenv('DEV_ID')
PATH_TO_DB = ROOT_DIR + '/' + os.getenv('DB_NAME')
PATH_TO_TRANSLATIONS = ROOT_DIR + '/languages'
DEFAULT_LANG = 'en'

LINGVOLIVE_API_KEY = os.getenv('LINGVOLIVE_API_KEY')
QUOTE_API_ENDPOINT = os.getenv('QUOTE_API_ENDPOINT')
