# -*- coding: utf-8 -*-

# ===== External libs imports =====

from aiogram.dispatcher.filters.state import State, StatesGroup


class DictionaryState(StatesGroup):
    dictionary = State()
    statistics = State()
    quiz = State()


class DictionaryAddNewWordState(StatesGroup):
    word = State()
    translation = State()
    confirmation = State()


class DictionaryDeleteWordState(StatesGroup):
    search_query = State()
    confirmation = State()


class DictionaryEditWordState(StatesGroup):
    search_query = State()
    new_value = State()
    confirmation = State()


class DictionarySearchWordState(StatesGroup):
    search_query = State()
    confirmation = State()


class DictionaryQuizState(StatesGroup):
    quiz_data = State()
    user_answers = State()
    index = State()
    quiz_results = State()
    finish = State()
