# -*- coding: utf-8 -*-

# TODO: Add antiflood middleware
# TODO: Try to change polling to webhook on local server just for performance tests
# TODO: Learn handling bot unique links for some actions (like referral links)
# TODO: Learn how to improve performance (throttling examples)
# TODO: Create mechanism for mass messaging (newsletter)
# TODO: Along with mass messaging mechanism implement the daily(or weakly) personal quizzes for all users (+settings)
# TODO: After implementing basic functions (Add, Delete, Edit, Find) - test spell checking ready solutions

# TODO: Refactor all handlers to separate files with class that initializing its own logical message handlers

# ===== Default imports =====

import logging

# ===== External libs imports =====

from aiogram import Bot, Dispatcher, executor

# ===== Local imports =====

import config
from vocabulary_bot import VocabularyBot

# ===== Basic initializations =====

logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.TOKEN)
dp = Dispatcher(bot)
vocabulary_bot = VocabularyBot(dp)


def main():
    """Application entry point"""
    # TODO: Change to webhooks in production
    executor.start_polling(vocabulary_bot.dp, skip_updates=True)


if __name__ == '__main__':
    main()
