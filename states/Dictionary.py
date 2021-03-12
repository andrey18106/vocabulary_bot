# -*- coding: utf-8 -*-

# ===== External libs imports =====

from aiogram.dispatcher.filters.state import State, StatesGroup


class DictionaryAddNewWordState(StatesGroup):
    word = State()
    translation = State()
    confirmation = State()


class DictionaryDeleteWordState(StatesGroup):
    search_query = State()
    confirmation = State()


class DictionarySearchWordState(StatesGroup):
    search_query = State()
