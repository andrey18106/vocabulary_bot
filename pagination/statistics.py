# -*- coding: utf-8 -*-

# ===== External libs imports =====

from aiogram import types

# ===== Local imports =====

from db_manager import DbManager
from lang_manager import LangManager
from markups_manager import MarkupManager
from .Paginator import Paginator


class StatisticsPaginator(Paginator):
    action = 'statistics'
    parse_mode = 'Markdown'

    def __init__(self, lang_manager: LangManager, db_manager: DbManager, markup_manager: MarkupManager, user_id: int,
                 current_page: dict = None):
        super().__init__()
        self.user_id = user_id
        self.lang = lang_manager
        self.db = db_manager
        self.markup = markup_manager
        self.user_last_word_added = self.db.get_user_dict_last_word_date(self.user_id)
        self.from_lang = current_page['from_lang']
        self.to_lang = current_page['to_lang']
        self.data = self.db.get_user_dictionary_stats(self.user_id, self.from_lang, self.to_lang)
        if self.data is not None:
            self.total_pages = self.data['total_pages']
            self.current_state = current_page
            self.current_year_index = self.current_state['current_year_index']
            self.current_month_index = self.current_state['current_month_index']
            self.current_month_page = self.current_state['current_month_page']
            self.current_total_page = self.current_state['current_total_page']
            self.current_year = self.__parse_year()
            self.current_month = self.__parse_month()

    def first(self):
        self.current_year_index = 0
        self.current_year = self.__parse_year()
        self.current_month_index = 0
        self.current_month = self.__parse_month()
        self.current_month_page = 0
        self.current_total_page = 0

    def prev(self):
        if self.current_month_page > 0:
            self.current_month_page -= 1
            self.current_total_page -= 1
        elif self.current_month_index > 0:
            self.current_month_index -= 1
            self.current_month = self.__parse_month()
            self.current_month_page = self.data['years'][self.current_year]['months'][self.current_month][
                                          'pages'] - 1
            self.current_total_page -= 1
        elif self.current_year_index > 0:
            self.current_year_index -= 1
            self.current_year = self.__parse_year()
            self.current_month_index = len(self.data['years'][self.current_year]['months']) - 1
            self.current_month = self.__parse_month()
            self.current_month_page = self.data['years'][self.current_year]['months'][self.current_month][
                                          'pages'] - 1
            self.current_total_page -= 1

    def next(self):
        if self.current_month_page < self.data['years'][self.current_year]['months'][self.current_month]['pages'] - 1:
            self.current_month_page += 1
            self.current_total_page += 1
        elif len(self.data['years'][self.current_year]['months']) > 1 \
                and self.current_month_index < len(self.data['years'][self.current_year]['months']) - 1:
            self.current_month_index += 1
            self.current_month = self.__parse_month()
            self.current_month_page = 0
            self.current_total_page += 1
        elif len(self.data['years']) > 1 and self.current_year_index < len(self.data['years']) - 1:
            self.current_year_index += 1
            self.current_year = self.__parse_year()
            self.current_month_index = 0
            self.current_month = self.__parse_month()
            self.current_month_page = 0
            self.current_total_page += 1

    def last(self):
        self.current_year_index = len(self.data['years']) - 1
        self.current_year = self.__parse_year()
        self.current_month_index = len(self.data['years'][self.current_year]['months']) - 1
        self.current_month = self.__parse_month()
        self.current_month_page = self.data['years'][self.current_year]['months'][self.current_month]['pages'] - 1
        self.current_total_page = self.total_pages - 1

    def first_page(self, lang_code: str) -> str:
        self.first()
        return self.lang.get_user_dict_stats_page(self.data, self.current_year, self.current_month,
                                                  self.current_month_page, self.current_total_page, lang_code)

    def prev_page(self, lang_code: str) -> str:
        self.prev()
        return self.lang.get_user_dict_stats_page(self.data, self.current_year, self.current_month,
                                                  self.current_month_page, self.current_total_page, lang_code)

    def next_page(self, lang_code: str) -> str:
        self.next()
        return self.lang.get_user_dict_stats_page(self.data, self.current_year, self.current_month,
                                                  self.current_month_page, self.current_total_page, lang_code)

    def last_page(self, lang_code: str) -> str:
        self.last()
        return self.lang.get_user_dict_stats_page(self.data, self.current_year, self.current_month,
                                                  self.current_month_page, self.current_total_page, lang_code)

    def is_first(self) -> bool:
        return self.current_total_page == 0

    def is_last(self) -> bool:
        return self.current_total_page == self.total_pages - 1

    def get_pages_count(self) -> int:
        return self.total_pages - 1

    def get_reply_markup(self) -> types.InlineKeyboardMarkup:
        return self.markup.get_pagination_markup(action=self.action)

    def get_parse_mode(self):
        return self.parse_mode

    def get_state_data(self):
        self.current_state = {
            'current_year_index': self.current_year_index,
            'current_month_index': self.current_month_index,
            'current_month_page': self.current_month_page,
            'current_total_page': self.current_total_page,
            'from_lang': self.from_lang,
            'to_lang': self.to_lang
        }
        return self.current_state

    def __parse_year(self):
        return tuple(tuple(self.data['years'].items()))[self.current_year_index][0]

    def __parse_month(self):
        return tuple(tuple(self.data['years'].items())[self.current_year_index][1]['months'].items())[
            self.current_month_index][0]
