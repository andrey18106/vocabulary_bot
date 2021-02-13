# -*- coding: utf-8 -*-

# ===== Default imports =====

import logging

# ===== External libs imports =====

from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# ===== Local imports =====

import config
from vocabulary_bot import VocabularyBot

# ===== Basic initializations =====

logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
vocabulary_bot = VocabularyBot(bot, dp)


def main():
    """Application entry point"""
    # TODO: Change to webhooks in production
    executor.start_polling(dispatcher=vocabulary_bot.dp,
                           skip_updates=True,
                           on_shutdown=vocabulary_bot.shutdown)


if __name__ == '__main__':
    main()
