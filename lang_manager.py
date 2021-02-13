# -*- coding: utf-8 -*-

# TODO: Change json to common localization file type (*.po, like in aiogram docs i18n)

# ===== Default imports =====

import json
import logging
import os

# ===== Local imports =====

from config import ROOT_DIR, DEFAULT_LANG

# ===== Local imports =====

from db_manager import DbManager


class LangManager:
    """Class for working with bot localization"""

    def __init__(self, path_to_translations: str, db_manager: DbManager):
        """Initializing existing localizations"""
        self.path_to_translations = path_to_translations
        self.db = db_manager
        self.localizations = {}
        self.init_localizations()

    def init_localizations(self):
        """Initialize files with translation and provide list of available translations"""
        if os.path.isdir(self.path_to_translations):
            translations = os.listdir(self.path_to_translations)
            for translation in translations:
                path_to_translation = os.path.join(ROOT_DIR, self.path_to_translations, translation)
                with(open(path_to_translation, 'r', encoding='utf-8')) as file:
                    try:
                        self.localizations[os.path.splitext(translation)[0]] = json.loads(file.read())
                    except FileNotFoundError as error:
                        logging.getLogger(type(self).__name__).error(error)
            logging.getLogger(type(self).__name__).info(
                f'Localizations successfully initialized! [{len(self.localizations)}]')

    def get(self, key: str, lang_code: str) -> str:
        """Returns translation by [key] for given [lang_code]"""
        if lang_code in self.localizations:
            return self.localizations[lang_code][key]
        else:
            return self.localizations[DEFAULT_LANG][key]

    def parse_user_lang(self, user_id: int) -> str:
        """Returns language code according to uses settings. If user hasn't lang settings returns default lang"""
        return self.db.get_user_lang(user_id) if self.db.is_user_exists(user_id) else DEFAULT_LANG

    def get_markup_localization(self, key: str, lang_code: str) -> dict:
        """Returns list of button texts for markup"""
        if lang_code in self.localizations and key in self.localizations[lang_code]:
            return self.localizations[lang_code][key]['BUTTONS']
        else:
            return self.localizations[DEFAULT_LANG][key]['BUTTONS']

    def get_page_text(self, key: str, value: str, lang_code: str) -> str:
        """Returns lang settings text"""
        if lang_code in self.localizations and key in self.localizations[lang_code]:
            return self.localizations[lang_code][key][value]
        else:
            return self.localizations[DEFAULT_LANG][key][value]

    def get_inline_markup_localization(self, key: str, lang_code: str) -> list:
        """Returns list of inline button texts with callbacks data"""
        if lang_code in self.localizations and key in self.localizations[lang_code]:
            return self.localizations[lang_code][key]['BUTTONS']
        else:
            return self.localizations[DEFAULT_LANG][key]['BUTTONS']

    def get_user_dict(self, user_id: int, lang_code: str) -> str:
        """TODO: Implement user dict output"""
        user_dict = self.db.get_user_dict(user_id)
        result_string = self.get_page_text('DICTIONARY', 'TEXT', lang_code)
        if len(user_dict) > 10:
            for word in user_dict:
                result_string += word + '\n'
        elif len(user_dict) > 0:
            first_batch_of_dict = [user_dict[i] for i in range(0, 10)]
            result_string += first_batch_of_dict
        return result_string
