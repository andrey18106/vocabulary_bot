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

    def __init__(self, lang_manager: LangManager, db_manager: DbManager, markup_manager: MarkupManager, user_id: int,
                 current_page: int = 0):
        super().__init__()
        self.user_id = user_id
        self.lang = lang_manager
        self.db = db_manager
        self.markup = markup_manager
        self.user_last_word_added = self.db.get_user_dict_last_word_date(self.user_id)
        self.data = self.db.get_user_dictionary_stats(self.user_id)
        self.current_page = current_page

    def first(self):
        self.current_page = 0

    def prev(self):
        if self.current_page > 0:
            self.current_page -= 1

    def next(self):
        if self.current_page < self.data['total_pages']:
            self.current_page += 1

    def last(self):
        self.current_page = self.data['total_pages']

    def first_page(self, lang_code: str) -> str:
        return self.lang.get_user_dict_stats_page(self.data, self.user_last_word_added.year,
                                                  self.user_last_word_added.month, self.current_page, lang_code)

    def prev_page(self, lang_code: str) -> str:
        return self.lang.get_user_dict_stats_page(self.data, self.user_last_word_added.year,
                                                  self.user_last_word_added.month, self.current_page, lang_code)

    def next_page(self, lang_code: str) -> str:
        return self.lang.get_user_dict_stats_page(self.data, self.user_last_word_added.year,
                                                  self.user_last_word_added.month, self.current_page, lang_code)

    def last_page(self, lang_code: str) -> str:
        return self.lang.get_user_dict_stats_page(self.data, self.user_last_word_added.year,
                                                  self.user_last_word_added.month, self.current_page, lang_code)

    def is_first(self) -> bool:
        return self.current_page == 0

    def is_last(self) -> bool:
        return self.current_page == self.data['total_pages']

    def get_pages_count(self) -> int:
        return self.data['total_pages']

    def get_reply_markup(self) -> types.InlineKeyboardMarkup:
        return self.markup.get_pagination_markup(action=self.action)
