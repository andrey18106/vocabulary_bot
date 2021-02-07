# -*- coding: utf-8 -*-

from dotenv import load_dotenv
import os
from pathlib import Path

ROOT_DIR = Path('.')
env_path = ROOT_DIR / '.env'
load_dotenv(dotenv_path=env_path)

TOKEN = os.getenv('TOKEN')
DEV_ID = os.getenv('DEV_ID')
PATH_TO_DB = Path('.') / os.getenv('DB_NAME')
PATH_TO_TRANSLATIONS = Path('.') / 'languages'
DEFAULT_LANG = 'en'
