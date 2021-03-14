# -*- coding: utf-8 -*-

# ===== External libs imports =====

from aiogram.dispatcher.filters.state import State, StatesGroup


class AdminDatabaseState(StatesGroup):
    query = State()
