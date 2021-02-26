# -*- coding: utf-8 -*-

# ===== Default imports =====

from datetime import datetime
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
        if lang_code in self.localizations and key in self.localizations[lang_code]:
            return self.localizations[lang_code][key]
        elif key in self.localizations[DEFAULT_LANG]:
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
        result_string = ''
        if len(user_dict) > 0:
            for word in user_dict:
                result_string += f'[{word[3]} - {word[4]}]. '
                result_string += f'{word[1]} - {word[2]} /word_{str(word[0])}\n'
        else:
            result_string = self.get_page_text('DICTIONARY', 'EMPTY_DICTIONARY', lang_code)
        return result_string

    def get_word_info(self, word_id: int, user_id: int, user_lang: str) -> str:
        if self.db.word_in_user_dict(word_id, user_id):
            word_info = self.db.get_user_word(word_id, user_id)
            word_info_str = self.get_page_text('DICTIONARY', 'WORD_INFO', user_lang) + ':\n\n'
            word_info_str += f'{word_info[2]} - {word_info[3]}'
        else:
            word_info_str = self.get_page_text('DICTIONARY', 'NOT_FOUND', user_lang)
        return word_info_str

    def get_admin_statistics_page(self, user_id: int, lang_code: str) -> str:
        if self.db.is_admin(user_id):
            statistics = self.db.get_admin_statistics()
            statistics_string = self.get_page_text('ADMIN', 'STATISTICS', lang_code) + ':\n\n'
            for stat in statistics:
                statistics_string += f'{stat[2]} [{stat[1]}]\n'
            return statistics_string

    def get_words_api_page(self, user_id: int, user_lang: str) -> str:
        words_api_page = 'WORDS API STATS:\n\n'
        words_api_page += str(self.db.get_words_api_stats())
        return words_api_page

    def get_admin_users_page(self, lang_code: str) -> str:
        users_list = self.db.get_users_list()
        users_page = self.get_page_text('ADMIN', 'USERS', lang_code) + '\n\n'
        users_page += str(len(users_list))
        return users_page

    def get_database_page(self, lang_code: str) -> str:
        return self.get_page_text('ADMIN', 'DATABASE', lang_code)

    def get_user_profile_page(self, user_id: int, lang_code: str) -> str:
        user_info = self.db.get_user_info(user_id)
        user_info_date = user_info[5].split('-')
        user_date_from = datetime(int(user_info_date[0]), int(user_info_date[1]), int(user_info_date[2])).strftime(
            "%d.%m.%Y")
        user_profile_page = self.get_page_text('PROFILE', 'TEXT', lang_code) + '\n\n'
        user_profile_page += f'*{self.get_page_text("PROFILE", "DATE_FROM", lang_code)}*: {user_date_from}\n'
        user_profile_page += f'*{self.get_page_text("PROFILE", "LANG_SETTING", lang_code)}*: {user_info[4]}\n'
        user_profile_page += f'*{self.get_page_text("PROFILE", "DICT_CAPACITY", lang_code)}*: ' \
                             f'{self.db.get_user_dict_info(user_id)}\n'
        user_profile_page += f'*{self.get_page_text("PROFILE", "REFERRALS", lang_code)}*: ' \
                             f'{self.db.get_user_referral_count(user_id)}'
        return user_profile_page
