# -*- coding: utf-8 -*-

# ===== External libs imports =====

from aiogram import Dispatcher, types

# ===== Local imports =====

import config
from admin_manager import AdminManager
from analytics import BotAnalytics
from db_manager import DbManager
from handlers.callback_handlers import VocabularyBotCallbackHandler
from lang_manager import LangManager
from markups_manager import MarkupManager


class VocabularyBot:
    """Basic class for Vocabulary Bot necessary logics"""

    def __init__(self, dispatcher: Dispatcher):
        self.dp = dispatcher

        self.db = DbManager(config.PATH_TO_DB)
        self.db.create_connection()
        self.lang = LangManager(config.PATH_TO_TRANSLATIONS, self.db)
        self.markup = MarkupManager(self.lang)
        self.analytics = BotAnalytics(self.db)
        self.admin = AdminManager(self.db, self.lang, self.markup, self.dp, self.analytics)
        self.admin.init_message_handlers()

        self.callbacks = VocabularyBotCallbackHandler(self.db, self.lang, self.markup, self.analytics, self.dp)

        self.__init_handlers()

    def __init_handlers(self):
        @self.dp.message_handler(commands=['start', 'help'])
        @self.analytics.default_metric
        async def welcome_message_handler(message: types.Message):
            """`/start` and `/help`commands handler"""
            if self.db.is_user_exists(message['from']['id']):
                user_lang = self.db.get_user_lang(message['from']['id'])
            else:
                self.db.add_user(message['from']['id'], message['from']['username'], message['from']['first_name'],
                                 message['from']['last_name'])
                self.db.set_user_lang(message['from']['id'], config.DEFAULT_LANG)
                user_lang = config.DEFAULT_LANG
            await message.answer(text=self.lang.get('WELCOME_MESSAGE', user_lang),
                                 reply_markup=self.markup.get_main_menu_markup(user_lang))

        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_page_text('BACK_MAIN_MENU', 'BUTTON', self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG)))
        @self.analytics.default_metric
        async def back_main_menu_command_handler(message: types.Message):
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text('BACK_MAIN_MENU', 'TEXT', user_lang),
                                 reply_markup=self.markup.get_main_menu_markup(user_lang))

        # IF MAIN_MENU -> DICTIONARY COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("MAIN_MENU", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[0])
        @self.analytics.default_metric
        async def dictionary_command_handler(message: types.Message):
            """TODO: Handler for dictionary command (📃 Dictionary)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text('DICTIONARY', 'TEXT', user_lang),
                                 reply_markup=self.markup.get_dictionary_markup(user_lang))
            await message.answer(text=self.lang.get_user_dict(message['from']['id']),
                                 reply_markup=self.markup.get_dict_pagination(message['from']['id'], user_lang))

        # IF MAIN_MENU -> ACHIEVEMENTS COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("MAIN_MENU", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[1])
        @self.analytics.default_metric
        async def achievements_command_handler(message: types.Message):
            """TODO: Achievements page"""
            pass

        # IF MAIN_MENU -> RATING COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("MAIN_MENU", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[2])
        @self.analytics.default_metric
        async def rating_command_handler(message: types.Message):
            """TODO: Rating page"""
            pass

        # IF MAIN_MENU -> SETTINGS COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("MAIN_MENU", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[3])
        @self.analytics.default_metric
        async def settings_command_handler(message: types.Message):
            """Handler for settings command (⚙ Settings)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text("LANG_SETTINGS", "TEXT", user_lang),
                                 reply_markup=self.markup.get_lang_settings_markup(user_lang))

        # IF MAIN_MENU -> HELP COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("MAIN_MENU", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[4])
        @self.analytics.default_metric
        async def help_command_handler(message: types.Message):
            """Handler for settings command (❓ Help)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text('HELP', 'TEXT', user_lang),
                                 reply_markup=self.markup.get_help_markup(user_lang))

        # IF MAIN_MENU -> ADD WORD COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[0])
        @self.analytics.default_metric
        async def new_word_command_handler(message: types.Message):
            """Handler for add new word command (➕ Add word)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get('ECHO_MESSAGE', user_lang))

        # IF MAIN_MENU -> DELETE WORD COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[1])
        @self.analytics.default_metric
        async def delete_word_command_handler(message: types.Message):
            """TODO: Handler for delete word command (➖ Delete word)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get('ECHO_MESSAGE', user_lang))

        # IF MAIN_MENU -> EDIT WORD COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[2])
        @self.analytics.default_metric
        async def edit_word_command_handler(message: types.Message):
            """TODO: Handler for edit word command (✏ Edit word)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get('ECHO_MESSAGE', user_lang))

        # IF MAIN_MENU -> FIND WORD COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[3])
        @self.analytics.default_metric
        async def find_word_command_handler(message: types.Message):
            """TODO: Handler for edit word command (🔎 Find word)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get('ECHO_MESSAGE', user_lang))

        # IF MAIN_MENU -> QUIZ WORD COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[4])
        @self.analytics.default_metric
        async def quiz_command_handler(message: types.Message):
            """TODO: Handler for edit word command (📝 Quiz)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get('ECHO_MESSAGE', user_lang))

        @self.dp.message_handler()
        @self.analytics.default_metric
        async def echo_message_handler(message: types.Message):
            """Default message handler for unrecognizable messages"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get('ECHO_MESSAGE', user_lang))
