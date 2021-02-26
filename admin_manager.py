# -*- coding: utf-8 -*-

# ===== Default imports =====

import asyncio
import logging
import time

# ===== External libs imports =====

from aiogram import Bot, Dispatcher, types
from aiogram.utils import exceptions

# ===== Local imports =====

from analytics import BotAnalytics
from antiflood import rate_limit
from db_manager import DbManager
from lang_manager import LangManager
from markups_manager import MarkupManager


class AdminManager:
    """Class for working with admin functions"""

    def __init__(self, bot: Bot, db_manager: DbManager, lang_manager: LangManager, markup_manager: MarkupManager,
                 dispatcher: Dispatcher, analytics: BotAnalytics):
        self.bot = bot
        self.dp = dispatcher
        self.db = db_manager
        self.lang = lang_manager
        self.markup = markup_manager
        self.analytics = analytics
        self.permissions = self.db.get_permissions_list()
        self.__init_message_handlers()

    def __init_message_handlers(self):
        """Register admin command handlers"""

        @self.dp.message_handler(commands=['admin'])
        @rate_limit(1, 'admin')
        @self.analytics.default_metric
        async def admin_command_message_handler(message: types.Message):
            """`/admin` command handler"""
            if self.db.is_admin(message['from']['id']):
                user_lang = self.lang.parse_user_lang(message['from']['id'])
                await message.answer(text=self.lang.get_page_text('ADMIN', 'ADMIN_PANEL_TEXT', user_lang),
                                     reply_markup=self.markup.get_admin_markup(
                                         self.get_admin_permissions(message['from']['id']), user_lang))

        @self.dp.message_handler(commands=['default'])
        @rate_limit(1, 'default')
        @self.analytics.default_metric
        async def default_command_message_handler(message: types.Message):
            """`/default` command handler"""
            if self.db.is_admin(message['from']['id']):
                user_lang = self.lang.parse_user_lang(message['from']['id'])
                await message.answer(text=self.lang.get_page_text('ADMIN', 'DEFAULT_PANEL_TEXT', user_lang),
                                     reply_markup=self.markup.get_main_menu_markup(user_lang))

        @self.dp.message_handler(commands=['ping'])
        @rate_limit(1, 'ping')
        @self.analytics.default_metric
        async def ping_command_message_handler(message: types.Message):
            """`/ping` command handler"""
            if self.db.is_admin(message['from']['id']):
                start_time = time.time()
                message = await message.reply('Pong!')
                delta = time.time() - start_time
                await message.edit_text(text=f'Pong! *(reply took {delta:.2f}s)*', parse_mode='Markdown')

        # IF ADMIN PANEL -> USERS
        @self.dp.message_handler(lambda message: message.text == self.lang.get_page_text('ADMIN', 'BUTTONS',
                                                                                         self.lang.parse_user_lang(
                                                                                             message['from'][
                                                                                                 'id']))[0])
        @self.analytics.default_metric
        async def admin_users_command_handler(message: types.Message):
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_admin_users_page(user_lang))

        # IF ADMIN PANEL -> MAILINGS
        @self.dp.message_handler(lambda message: message.text == self.lang.get_page_text('ADMIN', 'BUTTONS',
                                                                                         self.lang.parse_user_lang(
                                                                                             message['from'][
                                                                                                 'id']))[1])
        @self.analytics.default_metric
        async def admin_mailings_command_handler(message: types.Message):
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text('ADMIN', 'MAILINGS', user_lang))

        # IF ADMIN PANEL -> ANALYTICS
        @self.dp.message_handler(lambda message: message.text == self.lang.get_page_text('ADMIN', 'BUTTONS',
                                                                                         self.lang.parse_user_lang(
                                                                                             message['from'][
                                                                                                 'id']))[2])
        @self.analytics.default_metric
        async def admin_analytics_command_handler(message: types.Message):
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_admin_statistics_page(message['from']['id'], user_lang))

        # IF ADMIN PANEL -> DATABASE
        @self.dp.message_handler(lambda message: message.text == self.lang.get_page_text('ADMIN', 'BUTTONS',
                                                                                         self.lang.parse_user_lang(
                                                                                             message['from'][
                                                                                                 'id']))[3])
        @self.analytics.default_metric
        async def admin_database_command_handler(message: types.Message):
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_database_page(user_lang),
                                 reply_markup=self.markup.get_admin_database_markup(user_lang))

    def get_admin_permissions(self, user_id: int) -> list:
        """
        TODO: Implement admin permissions
        1 Administrator: All permissions (all functions, statistics, mailings, vocabularies, admins)
        2 Moderator: Vocabulary permission (can manage vocabulary, mailings)
        3 Teacher: Vocabulary permission, Referral system for students
        """
        return self.permissions

    async def __send_mailing(self, user_id: int, text: str, disable_notification: bool = False) -> bool:
        """Safe messages sender"""
        try:
            await self.bot.send_message(user_id, text, disable_notification=disable_notification)
        except exceptions.BotBlocked:
            logging.getLogger(type(self).__name__).error(f"Target [ID:{user_id}]: blocked by user")
        except exceptions.ChatNotFound:
            logging.getLogger(type(self).__name__).error(f"Target [ID:{user_id}]: invalid user ID")
        except exceptions.RetryAfter as e:
            logging.getLogger(type(self).__name__).error(
                f"Target [ID:{user_id}]: Flood limit is exceeded. Sleep {e.timeout} seconds.")
            await asyncio.sleep(e.timeout)
            return await self.__send_mailing(user_id, text)  # Recursive call
        except exceptions.UserDeactivated:
            logging.getLogger(type(self).__name__).error(f"Target [ID:{user_id}]: user is deactivated")
        except exceptions.TelegramAPIError:
            logging.getLogger(type(self).__name__).exception(f"Target [ID:{user_id}]: failed")
        else:
            logging.getLogger(type(self).__name__).info(f"Target [ID:{user_id}]: success")
            return True
        return False

    async def broadcast(self, user_ids: list, text: str, notification: bool = False) -> None:
        """Simple mass messaging mechanism (20 messages per second, the limit - 30/sec)"""
        count = 0
        try:
            for user_id in user_ids:
                if await self.__send_mailing(user_id, text, disable_notification=notification):
                    count += 1
                await asyncio.sleep(.05)  # For message per second limit (20/s)
        finally:
            logging.getLogger(type(self).__name__).info(f'{count} messages successful sent.')
