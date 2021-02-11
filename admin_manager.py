# -*- coding: utf-8 -*-

# ===== External libs imports =====

from aiogram import Dispatcher, types

# ===== Local imports =====

from analytics import BotAnalytics
from db_manager import DbManager
from lang_manager import LangManager
from markups_manager import MarkupManager


class AdminManager:
    """Class for working with admin functions"""

    def __init__(self, db_manager: DbManager, lang_manager: LangManager, markup_manager: MarkupManager,
                 dispatcher: Dispatcher, analytics: BotAnalytics):
        self.db = db_manager
        self.lang = lang_manager
        self.markup = markup_manager
        self.analytics = analytics
        self.dp = dispatcher
        self.permissions = self.db.get_permissions_list()

    def init_message_handlers(self):
        """Register admin command handlers"""

        @self.dp.message_handler(commands=['admin'])
        @self.analytics.default_metric
        async def admin_command_message_handler(message: types.Message):
            """TODO: `/admin` command handler"""
            if self.db.is_admin(message['from']['id']):
                user_lang = self.lang.parse_user_lang(message['from']['id'])
                await message.answer(text=self.lang.get_page_text('ADMIN', 'ADMIN_PANEL_TEXT', user_lang),
                                     reply_markup=self.markup.get_admin_markup(
                                         self.get_admin_permissions(message['from']['id']), user_lang))

        @self.dp.message_handler(commands=['default'])
        @self.analytics.default_metric
        async def default_command_message_handler(message: types.Message):
            """TODO: `/default` command handler"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text('ADMIN', 'DEFAULT_PANEL_TEXT', user_lang),
                                 reply_markup=self.markup.get_main_menu_markup(user_lang))

    def get_admin_permissions(self, user_id: int) -> list:
        """
        TODO: Implement admin permissions
        Administrator: All permissions (can manage all functions)
        Moderator: Vocabulary permission (can manage vocabulary)
        """
        return self.permissions
