# -*- coding: utf-8 -*-

# ===== External libs imports =====

from aiogram import types

# ===== Local imports =====

from db_manager import DbManager
from lang_manager import LangManager
from markups_manager import MarkupManager
from .Paginator import Paginator


class AnalyticsPaginator(Paginator):

    action = 'analytics'

    def __init__(self, lang_manager: LangManager, db_manager: DbManager, markup_manager: MarkupManager, user_id: int,
                 current_page: int = 0):
        super().__init__()
        self.user_id = user_id
        self.lang = lang_manager
        self.db = db_manager
        self.markup = markup_manager
        self.data = self.db.get_user_achievements(self.user_id)
        self.current_page = current_page

    def first(self):
        self.current_page = 0

    def prev(self):
        if self.current_page > 0:
            self.current_page -= 1

    def next(self):
        if self.current_page < len(self.data):
            self.current_page += 1

    def last(self):
        self.current_page = self.last_page

    def first_page(self, lang_code: str) -> str:
        return ''

    def prev_page(self, lang_code: str) -> str:
        return ''

    def next_page(self, lang_code: str) -> str:
        return ''

    def last_page(self, lang_code: str) -> str:
        return ''

    def is_first(self) -> bool:
        return self.current_page == 0

    def is_last(self) -> bool:
        return self.current_page == len(self.data)

    def get_pages_count(self) -> int:
        return len(self.data)

    def get_reply_markup(self) -> types.InlineKeyboardMarkup:
        return self.markup.get_pagination_markup(action=self.action)
