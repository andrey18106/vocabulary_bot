# -*- coding: utf-8 -*-

# ===== External libs imports =====

from aiogram import types

# ===== Local imports =====

from db_manager import DbManager
from lang_manager import LangManager
from markups_manager import MarkupManager
from .Paginator import Paginator


class DictionaryPaginator(Paginator):

    action = 'dictionary'

    def __init__(self, lang_manager: LangManager, db_manager: DbManager, markup_manager: MarkupManager, user_id: int,
                 current_page: int = 0):
        super().__init__()
        self.user_id = user_id
        self.lang = lang_manager
        self.db = db_manager
        self.markup = markup_manager
        self.data = self.db.get_user_dict(self.user_id)
        self.paginated_data = [self.data[x:x + self.lang.PAGINATION_PAGE_SIZE] for x in
                               range(0, len(self.data), self.lang.PAGINATION_PAGE_SIZE)]
        self.current_page = current_page

    def first(self) -> list:
        self.current_page = 0
        return self.paginated_data[0] if len(self.paginated_data) > 0 else []

    def prev(self) -> list:
        if self.current_page > 0:
            self.current_page -= 1
            return self.paginated_data[self.current_page]

    def next(self):
        if self.current_page < len(self.paginated_data) - 1:
            self.current_page += 1
            return self.paginated_data[self.current_page]

    def last(self):
        self.current_page = len(self.paginated_data) - 1
        return self.paginated_data[self.current_page]

    def first_page(self, lang_code: str) -> str:
        return self.lang.get_user_dict(self.first(), lang_code)

    def prev_page(self, lang_code: str) -> str:
        return self.lang.get_user_dict(self.prev(), lang_code)

    def next_page(self, lang_code: str) -> str:
        return self.lang.get_user_dict(self.next(), lang_code)

    def last_page(self, lang_code: str) -> str:
        return self.lang.get_user_dict(self.last(), lang_code)

    def is_first(self) -> bool:
        return self.current_page == 0

    def is_last(self) -> bool:
        return self.current_page == len(self.paginated_data) - 1

    def get_reply_markup(self) -> types.InlineKeyboardMarkup:
        return self.markup.get_pagination_markup(action=self.action) if len(self.data) > 10 else None

    def get_parse_mode(self):
        pass

    def get_pages_count(self) -> int:
        return len(self.paginated_data)

    def get_state_data(self):
        return self.current_page
