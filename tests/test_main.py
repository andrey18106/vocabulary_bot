# -*- coding: utf-8 -*-

# ===== Default imports =====

from dotenv import load_dotenv
import os
import unittest

# ===== External libs imports =====

from aiogram import Bot


class MainTest(unittest.IsolatedAsyncioTestCase):
    bot = None
    bot_info = None

    def setUp(self):
        load_dotenv(dotenv_path='../.env')

    async def asyncSetUp(self):
        self.bot = Bot(token=os.getenv('TOKEN'))
        self.bot_info = await self.bot.get_me()
        await self.bot.close()

    def test_main(self):
        self.assertEqual(self.bot_info['username'], 'vocabularies_bot')


if __name__ == '__main__':
    unittest.main()
