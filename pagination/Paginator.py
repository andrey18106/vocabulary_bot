# -*- coding: utf-8 -*-

# ===== Default imports =====

from abc import abstractmethod


class Paginator:

    def __init__(self):
        ...

    @abstractmethod
    def first(self):
        pass

    @abstractmethod
    def prev(self):
        pass

    @abstractmethod
    def next(self):
        pass

    @abstractmethod
    def last(self):
        pass

    @abstractmethod
    def first_page(self, lang_code: str) -> str:
        pass

    @abstractmethod
    def prev_page(self, lang_code: str) -> str:
        pass

    @abstractmethod
    def next_page(self, lang_code: str) -> str:
        pass

    @abstractmethod
    def last_page(self, lang_code: str) -> str:
        pass

    @abstractmethod
    def get_reply_markup(self):
        pass

    @abstractmethod
    def is_first(self):
        pass

    @abstractmethod
    def is_last(self):
        pass

    @abstractmethod
    def get_pages_count(self):
        pass
