# -*- coding: utf-8 -*-

# TODO: Refactor the project files structure (group by logical folders)
# TODO: Add command path checking (if typing manually command from the not reachable state (keyboard))
# TODO: Implement Finite State Machine for the command path checking
# TODO: The daily (or weakly) personal quizzes via mass messaging mechanism for users (+ appropriate user settings)
# TODO: After implementing basic functions (Add, Delete, Edit, Find, Stats ...) - test spell checking ready solutions
# TODO: Create reusable paginator for large pages
#  (Dictionary, Statistics, Rating, Achievements, Analytics, Users, Settings)

# ===== Default imports =====

import logging
import re

# ===== External libs imports =====

from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand
from aiogram.utils.exceptions import Throttled

# ===== Local imports =====

import config
from admin_manager import AdminManager
from analytics import BotAnalytics
from db_manager import DbManager
from callback_handlers import VocabularyBotCallbackHandler
from lang_manager import LangManager
from markups_manager import MarkupManager
from antiflood import rate_limit, ThrottlingMiddleware


class VocabularyBot:
    """Basic class for Vocabulary Bot necessary logics"""

    commands = [
        BotCommand(command='/start', description='Start the bot'),
        BotCommand(command='/help', description='Welcome message'),
        BotCommand(command='/ping', description='Check the latency'),
        BotCommand(command='/settings', description='Bot settings')
    ]

    def __init__(self, bot: Bot, dispatcher: Dispatcher):
        self.bot = bot
        self.dp = dispatcher
        self.dp.middleware.setup(ThrottlingMiddleware())

        self.db = DbManager(config.PATH_TO_DB)
        self.db.create_connection()
        self.lang = LangManager(config.PATH_TO_TRANSLATIONS, self.db)
        self.markup = MarkupManager(self.lang)
        self.analytics = BotAnalytics(self.db)
        self.admin = AdminManager(self.bot, self.db, self.lang, self.markup, self.dp, self.analytics)

        self.callbacks = VocabularyBotCallbackHandler(self.db, self.lang, self.markup, self.analytics, self.dp)

        self.__init_handlers()

    def __init_handlers(self):
        """Initializing basic Vocabulary Bot message handlers"""

        @self.dp.message_handler(commands=['start', 'help'])
        @rate_limit(5, 'start')
        @self.analytics.default_metric
        async def welcome_message_handler(message: types.Message):
            """`/start` and `/help`commands handler"""
            # HANDLE REFERRAL
            if message.get_args() is not None and re.match('referral_[0-9]*', message.get_args()):
                referrer_id = int(message.get_args()[9:])
                # IF REFERRER EXISTS AND REFERRAL USER IS NOT EXISTS IN THE DATABASE
                if self.db.is_user_exists(referrer_id) and message['from']['id'] != referrer_id \
                        and not self.db.is_user_exists(message['from']['id']):
                    self.db.update_referral_count(referrer_id)

            if self.db.is_user_exists(message['from']['id']):
                user_lang = self.db.get_user_lang(message['from']['id'])
            else:
                self.db.add_user(message['from']['id'], message['from']['username'], message['from']['first_name'],
                                 message['from']['last_name'])
                self.db.set_user_lang(message['from']['id'], config.DEFAULT_LANG)
                user_lang = config.DEFAULT_LANG
            await message.answer(text=self.lang.get('WELCOME_MESSAGE', user_lang),
                                 reply_markup=self.markup.get_main_menu_markup(user_lang))

        @self.dp.message_handler(commands=['cancel'])
        @self.analytics.default_metric
        async def cancel_command_handler(message: types.Message):
            """TODO: Add canceling current multi message command (after FSM implementation)"""
            ...

        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_page_text('BACK_MAIN_MENU', 'BUTTON', self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG)))
        @self.analytics.default_metric
        async def back_main_menu_command_handler(message: types.Message):
            """Back to main menu command handler"""
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
            await message.answer(text=self.lang.get_user_dict(message['from']['id'], user_lang),
                                 reply_markup=self.markup.get_dict_pagination('dictionary')
                                 if (len(self.db.get_user_dict(message['from']['id'])) > 0) else None)

        # IF MAIN_MENU -> ACHIEVEMENTS COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("MAIN_MENU", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[1])
        @self.analytics.default_metric
        async def achievements_command_handler(message: types.Message):
            """TODO: Achievements page"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text("ACHIEVEMENTS", "TEXT", user_lang))

        # IF MAIN_MENU -> RATING COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("MAIN_MENU", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[2])
        @self.analytics.default_metric
        async def rating_command_handler(message: types.Message):
            """TODO: Rating page"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text("RATING", "NOT_AVAILABLE", user_lang))

        # IF MAIN_MENU -> PROFILE COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("MAIN_MENU", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[
                3])
        @self.analytics.default_metric
        async def profile_command_handler(message: types.Message):
            """Handler for settings command (⚙ Profile)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_user_profile_page(message['from']['id'], user_lang),
                                 parse_mode='Markdown')

        # IF MAIN_MENU -> SETTINGS COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("MAIN_MENU", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[4])
        @self.analytics.default_metric
        async def settings_command_handler(message: types.Message):
            """Handler for settings command (⚙ Settings)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text("SETTINGS", "TEXT", user_lang),
                                 reply_markup=self.markup.get_settings_markup(user_lang))

        @self.dp.message_handler(commands=['settings'])
        @self.analytics.default_metric
        async def settings_command_handler(message: types.Message):
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text("SETTINGS", "TEXT", user_lang),
                                 reply_markup=self.markup.get_settings_markup(user_lang))

        # IF MAIN_MENU -> HELP COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("MAIN_MENU", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[5])
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
            """Handler for add new word command (➕ Add word)
            (in a future with selection the thematic vocabulary)
            TODO: Handle a new word via FSM
            Default Dictionary Command Logics:
            -> Send a welcome message according to the action to enter the new word
            -> Set the FSM state to "waiting for a new word"
            -> Handle the message with a new word
            -> Validate a new word (spell checking, translation, regexp for English words or phrases)
            -> Save a new word in the database if it correct (after previous step validation)
            -> Check for achievements receiving after this action executed
            -> Send motivational message
            """
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text('ADD_WORD', 'IN_DEVELOPING', user_lang))

        # IF MAIN_MENU -> DELETE WORD COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[1])
        @self.analytics.default_metric
        async def delete_word_command_handler(message: types.Message):
            """TODO: Handler for delete word command (➖ Delete word)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text('DELETE_WORD', 'IN_DEVELOPING', user_lang))

        # IF MAIN_MENU -> EDIT WORD COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[2])
        @self.analytics.default_metric
        async def edit_word_command_handler(message: types.Message):
            """TODO: Handler for edit word command (✏ Edit word)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text('EDIT_WORD', 'IN_DEVELOPING', user_lang))

        # IF MAIN_MENU -> FIND WORD COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[3])
        @self.analytics.default_metric
        async def find_word_command_handler(message: types.Message):
            """TODO: Handler for edit word command (🔎 Find word)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text('FIND_WORD', 'IN_DEVELOPING', user_lang))

        # IF MAIN_MENU -> QUIZ COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[4])
        @self.analytics.default_metric
        async def quiz_command_handler(message: types.Message):
            """TODO: Handler for edit word command (📝 Quiz)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text('QUIZ', 'IN_DEVELOPING', user_lang))

        # IF MAIN_MENU -> STATISTICS COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[5])
        @self.analytics.default_metric
        async def quiz_command_handler(message: types.Message):
            """TODO: Handler for edit word command (📉 Statistics)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text('STATISTICS', 'IN_DEVELOPING', user_lang))

        @self.dp.message_handler(lambda message: message.text.startswith('/word_'))
        @self.analytics.default_metric
        async def word_by_id_command_handler(message: types.Message):
            word_id = int(message.text[6:])
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_word_info(word_id, message['from']['id'], user_lang))

        @self.dp.message_handler()
        @self.analytics.default_metric
        async def echo_message_handler(message: types.Message):
            """Default message handler for unrecognizable messages"""
            try:
                await self.dp.throttle('echo', rate=2)
            except Throttled as error:
                logging.getLogger(type(self).__name__).error(error)
            else:
                user_lang = self.lang.parse_user_lang(message['from']['id'])
                await message.answer(text=self.lang.get('ECHO_MESSAGE', user_lang))

    async def init_commands(self):
        """Init commands and their descriptions"""
        await self.bot.set_my_commands(self.commands)

    async def shutdown(self):
        """Operations for safely bot shutdown"""
        self.db.close_connection()
