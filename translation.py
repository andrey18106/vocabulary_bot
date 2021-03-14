# -*- coding: utf-8 -*-

# ===== Default imports =====

from urllib.parse import quote

# ===== External libs imports =====

import requests


DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '\
                     'Chrome/89.0.4389.82 Safari/537.36 Edg/89.0.774.50'

headers = {
    'User-Agent': DEFAULT_USER_AGENT,
    'From': 'https://google.com/'
}

LEO_CONFIG = {
    'api': 'https://api.lingualeo.com',
    'get_translations': '/gettranslates',
    'translate': '/translate.php'
}


def google_translate(source_text: str, from_lang: str, to_lang: str) -> str:
    """Translate word or short phrase from one lang to another via Google Translate API"""
    url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=" \
          f"{from_lang}&tl={to_lang}&dt=t&q={quote(source_text)}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        result = ''
        for translated_string in data[0]:
            result += translated_string[0]
        return result
    return ''


def leo_translate(source_text: str):
    """Get a few word translations in English"""
    url = LEO_CONFIG['api'] + LEO_CONFIG['get_translations'] + f'?word={quote(source_text)}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        result = {
            'word': source_text,
            'transcription': data['transcription'],
            'translations': [translation['value'] for translation in data['translate']]
        }
        return result
    return None
