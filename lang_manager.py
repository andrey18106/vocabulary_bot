# -*- coding: utf-8 -*-

# ===== Default imports =====

import calendar
from datetime import datetime
import math
import json
import logging
import os

# ===== Local imports =====

from config import ROOT_DIR, DEFAULT_LANG
from db_manager import DbManager


class LangManager:
    """Class for working with bot localization and other text outputs"""

    PAGINATION_PAGE_SIZE = 10

    def __init__(self, path_to_translations: str, db_manager: DbManager):
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

    def get_admin_markup_localization(self, permissions: tuple, lang_code: str) -> list:
        if lang_code in self.localizations and 'PERMISSIONS' in self.localizations[lang_code]['ADMIN']:
            return self.localizations[lang_code]['ADMIN']['PERMISSIONS'][permissions[0] - 1]['BUTTONS']
        else:
            return self.localizations[DEFAULT_LANG]['ADMIN']['PERMISSIONS'][permissions[0] - 1]['BUTTONS']

    def get_page_text(self, key: str, value: str, lang_code: str) -> str:
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

    def get_user_dict(self, user_dict: list, lang_code: str) -> str:
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

    def get_admin_statistics_page(self, statistics: list, lang_code: str) -> str:
        statistics_string = self.get_page_text('ADMIN', 'STATISTICS', lang_code) + ':\n\n'
        for stat in statistics:
            statistics_string += f'{stat[2]} [{stat[1]}]\n'
        return statistics_string

    def get_admin_users_page(self, lang_code: str) -> str:
        users_list = self.db.get_users_list()
        users_page = self.get_page_text('ADMIN', 'USERS', lang_code) + '\n\n'
        users_page += str(len(users_list))
        return users_page

    def get_database_page(self, lang_code: str) -> str:
        return self.get_page_text('ADMIN', 'DATABASE', lang_code)

    def _parse_mailings_level(self, mailings_level: int, lang_code: str) -> str:
        newsletter_levels = self.get_page_text("NEWSLETTER_SETTINGS", "LEVELS", lang_code)
        return newsletter_levels[mailings_level]

    def get_user_profile_page(self, user_id: int, lang_code: str) -> str:
        user_info = self.db.get_user_info(user_id)
        user_info_date = user_info[5].split('-')
        user_date_from = datetime(int(user_info_date[0]), int(user_info_date[1]), int(user_info_date[2])).strftime(
            "%d.%m.%Y")
        user_profile_page = self.get_page_text('PROFILE', 'TEXT', lang_code) + '\n\n'
        user_profile_page += f'*{self.get_page_text("PROFILE", "DATE_FROM", lang_code)}*: {user_date_from}\n'
        user_profile_page += f'*{self.get_page_text("PROFILE", "LANG_SETTING", lang_code)}*: {user_info[4]}\n'
        user_profile_page += f'*{self.get_page_text("PROFILE", "MAILINGS", lang_code)}*: ' \
                             f'{self._parse_mailings_level(user_info[8], lang_code)}\n'
        user_profile_page += f'*{self.get_page_text("PROFILE", "DICT_CAPACITY", lang_code)}*: ' \
                             f'{self.db.get_user_total_dict_capacity(user_id)}\n'
        user_profile_page += f'*{self.get_page_text("PROFILE", "REFERRALS", lang_code)}*: ' \
                             f'{self.db.get_user_referral_count(user_id)}'
        if self.db.get_user_referrer(user_id) is not None:
            referrer_info = self.db.get_user_info(self.db.get_user_referrer(user_id))
            user_profile_page += f'\n*{self.get_page_text("PROFILE", "REFERRER", lang_code)}*: ' \
                                 f'{referrer_info[2]} {referrer_info[3]} (@{referrer_info[1]})'
        return user_profile_page

    def get_user_referral_link_page(self, user_id: int, lang_code: str) -> str:
        user_referral_link = 'https://t.me/vocabularies_bot?start=referral_' + str(user_id)
        return self.get_page_text("PROFILE", "REFERRAL_LINK_TEXT", lang_code) + "\n\n" + user_referral_link

    def get_user_dict_stats_page(self, stats: dict, year: int, month: int, month_page: int, total_page: int,
                                 lang_code: str) -> str:
        result = self.get_page_text('DICT_STATS', 'HEADING', lang_code).format(total_page + 1, stats["total_pages"])
        result += self.get_page_text('DICT_STATS', 'YEAR', lang_code).format(year)
        result += f'\t\t*{calendar.month_name[int(month)]}*:\n\n'
        page_data = stats['years'][str(year)]['months'][str(month)]['stats'][month_page]
        for day in page_data:
            dt = datetime.strftime(datetime(int(year), int(month), int(day)), "%d.%m.%Y")
            result += self.get_page_text('DICT_STATS', 'DATE', lang_code).format(dt, page_data[day])
        result += self.get_page_text('DICT_STATS', 'MONTH_TOTAL', lang_code).format(
            calendar.month_name[int(month)], stats["years"][str(year)]["months"][str(month)]["total"])
        result += self.get_page_text('DICT_STATS', 'YEAR_TOTAL', lang_code).format(year,
                                                                                   stats["years"][str(year)]["total"])
        return result

    def get_rating_page(self, user_id: int, lang_code: str) -> str:
        result = self.get_page_text("RATING", "TEXT", lang_code) + ':\n\n'
        top10_rating_list = self.db.get_rating_list(10, 0)
        for i in range(0, len(top10_rating_list)):
            if top10_rating_list[i][0] == user_id:
                result += f'⚫ {i + 1}. '
            else:
                result += f'{i + 1}. '
            result += f'{top10_rating_list[i][1]} '
            result += f'({self.get_page_text("RATING", "AMOUNT", lang_code)}: {top10_rating_list[i][2]})'
        return result

    def get_quiz_results_page(self, quiz_results: list, lang_code: str) -> str:
        result = self.get_page_text('QUIZ', 'RESULTS', lang_code) + ':\n\n'
        correct_answers = 0
        for i in range(0, len(quiz_results)):
            result += f'{i + 1}. *{quiz_results[i]["word"]}* ' \
                      f'({self.get_page_text("QUIZ", "RESULT_USER_ANSWER", lang_code)}: ' \
                      f'{quiz_results[i]["options"][quiz_results[i]["selected_option"]]["text"]}'
            if quiz_results[i]['selected_option'] != quiz_results[i]['correct_option']:
                result += f' `[{quiz_results[i]["selected_option"] == quiz_results[i]["correct_option"]}], `'
                result += f'{self.get_page_text("QUIZ", "RESULT_CORRECT", lang_code)}: ' \
                          f'{quiz_results[i]["options"][quiz_results[i]["correct_option"]]["text"]})\n'
            else:
                result += f' `[{quiz_results[i]["selected_option"] == quiz_results[i]["correct_option"]}]`)\n'
                correct_answers += 1
        correct_percentage = math.floor(((correct_answers / len(quiz_results)) * 100))
        result += f'\n{self.get_page_text("QUIZ", "FINISH_TOTAL", lang_code)}: ' \
                  f'{correct_answers}/{len(quiz_results)} ({correct_percentage}%)'
        return result

    def get_achievements_page(self, user_id: int, lang_code: str) -> str:
        result = ''
        user_achievements = self.db.get_user_achievements(user_id)
        if len(user_achievements) > 0:
            for achievement in user_achievements:
                result += f'{achievement[0]} {achievement[1]} ({achievement[2]})'
        return result

    @staticmethod
    def paginated(data: list, items_per_page: int, page_number: int) -> list:
        return [data[x:x + items_per_page] for x in range(0, len(data), 10)][page_number]

    def get_dictionary_list_markup(self, lang_code: str) -> list:
        if lang_code in self.localizations and 'DICTIONARY' in self.localizations[lang_code]:
            return self.localizations[lang_code]['DICTIONARY']['LIST']
        else:
            return self.localizations[DEFAULT_LANG]['DICTIONARY']['LIST']
