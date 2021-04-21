# -*- coding: utf-8 -*-

# ===== External libs imports =====

from aiogram.dispatcher.filters.state import State, StatesGroup


class AdminMailingState(StatesGroup):
    message = State()
    confirmation = State()
    send = State()
