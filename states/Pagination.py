# -*- coding: utf-8 -*-

# ===== External libs imports =====

from aiogram.dispatcher.filters.state import State, StatesGroup


class PaginationState(StatesGroup):
    pagination_data = State()
    pagination_page = State()
