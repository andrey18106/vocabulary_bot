# -*- coding: utf-8 -*-

# ===== Default imports =====

import asyncio
import logging
import sys

# ===== External libs imports =====

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# ===== Local imports =====

import config
from vocabulary_bot import VocabularyBot


async def main(dev_mode: bool):
    """Application entry point"""
    # TODO: Change to webhooks in production

    # ===== Basic initializations =====

    logging.basicConfig(level=logging.INFO)
    if dev_mode:
        bot = Bot(token=config.TOKEN_DEV)
        logging.getLogger(__name__).info('Running in development mode')
    else:
        bot = Bot(token=config.TOKEN)
    storage = MemoryStorage()  # TODO: Change MemoryStorage to Redis
    dp = Dispatcher(bot, storage=storage)
    vocabulary_bot = VocabularyBot(bot, dp, dev_mode)

    await vocabulary_bot.init_commands()
    await dp.skip_updates()
    await dp.start_polling()
    await vocabulary_bot.shutdown()


if __name__ == '__main__':
    is_dev_mode = 'dev' in sys.argv
    asyncio.run(main(is_dev_mode))
