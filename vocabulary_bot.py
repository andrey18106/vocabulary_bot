# -*- coding: utf-8 -*-

# TODO: The daily (or weakly) personal quizzes via mass messaging mechanism for users (+ appropriate user settings)
# TODO: After implementing basic functions (Add, Delete, Edit, Find, Stats ...) - test spell checking ready solutions
# TODO: Create reusable paginator for large pages
#  (Dictionary, Statistics, Rating, Achievements, Analytics, Users, Settings)

# ===== Default imports =====

import asyncio
import logging
import re

# ===== External libs imports =====

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.types import BotCommand

# ===== Local imports =====

import config
from admin_manager import AdminManager
from analytics import BotAnalytics
from db_manager import DbManager
from callback_handlers import VocabularyBotCallbackHandler
from lang_manager import LangManager
from markups_manager import MarkupManager
from antiflood import rate_limit, ThrottlingMiddleware
from states.Dictionary import DictionaryAddNewWordState, DictionaryDeleteWordState, DictionaryQuizState, \
    DictionarySearchWordState, DictionaryEditWordState


class VocabularyBot:
    """Basic class for Vocabulary Bot necessary logics"""

    USERS_FOR_RATING_LIMIT = 10
    commands = [
        BotCommand(command='/start', description='Start the bot'),
        BotCommand(command='/help', description='Welcome message'),
        BotCommand(command='/settings', description='Bot settings'),
        BotCommand(command='/cancel', description='Cancel command executing'),
        BotCommand(command='/ping', description='Check the latency')
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

        self.callbacks = VocabularyBotCallbackHandler(self.db, self.lang, self.markup, self.analytics, self.dp,
                                                      self.bot)

        self.__init_handlers()

    def __init_handlers(self):
        """Initializing basic Vocabulary Bot message handlers"""

        @self.dp.message_handler(commands=['start'])
        @rate_limit(5, 'start')
        @self.analytics.default_metric
        async def welcome_message_handler(message: types.Message):

            if self.db.is_user_exists(message['from']['id']):
                user_lang = self.lang.parse_user_lang(message['from']['id'])
            else:
                self.db.add_user(message['from']['id'], message['from']['username'], message['from']['first_name'],
                                 message['from']['last_name'])
                self.db.set_user_lang(message['from']['id'], config.DEFAULT_LANG)
                user_lang = config.DEFAULT_LANG

                # HANDLE REFERRAL
                if message.get_args() is not None and re.match('referral_[0-9]*', message.get_args()):
                    referrer_id = int(message.get_args()[9:])
                    # IF REFERRER EXISTS AND REFERRAL USER IS NOT EXISTS IN THE DATABASE
                    if self.db.is_user_exists(referrer_id) and message['from']['id'] != referrer_id:
                        self.db.update_referral_count(referrer_id)
                        self.db.set_user_referrer(message['from']['id'], referrer_id)
            await message.answer(text=self.lang.get('WELCOME_MESSAGE', user_lang),
                                 reply_markup=self.markup.get_main_menu_markup(user_lang))

        @self.dp.message_handler(commands=['help'])
        @rate_limit(3, 'help')
        @self.analytics.default_metric
        async def help_message_handler(message: types.Message):
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(self.lang.get('HELP_MESSAGE', user_lang))

        @self.dp.message_handler(state='*', commands=['cancel'])
        async def cancel_command_handler(message: types.Message, state: FSMContext):
            current_state = await state.get_state()
            if current_state is None:
                return
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            logging.getLogger(type(self).__name__).info('Cancelling state %r', current_state)
            await state.finish()
            await message.reply('Cancelled.', reply_markup=self.markup.get_main_menu_markup(user_lang))

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
            """Handler for dictionary command (📃 Dictionary)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text('DICTIONARY', 'TEXT', user_lang),
                                 reply_markup=self.markup.get_dictionary_markup(user_lang))
            await message.answer(text=self.lang.get_user_dict(message['from']['id'], user_lang),
                                 reply_markup=self.markup.get_pagination_markup('dictionary')
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
            await message.answer(text=self.lang.get_rating_page(message['from']['id'], user_lang)
                                 if len(self.db.get_rating_list(10, 0)) >= self.USERS_FOR_RATING_LIMIT else
                                 self.lang.get_page_text("RATING", "NOT_AVAILABLE", user_lang))

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
                                 parse_mode='Markdown',
                                 reply_markup=self.markup.get_profile_referral_markup(user_lang))

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
            Default Dictionary Command Logics:
            -> Send a welcome message according to the action to enter the new word
            -> Set the FSM state to "waiting for a new word"
            -> Handle the message with a new word
            -> Validate a new word (spell checking, translation, regexp for English words or phrases)
            -> Save a new word in the database if it correct (after previous step validation)
            -> Check for achievements receiving after this action executed
            -> Send motivational message
            """
            await DictionaryAddNewWordState.word.set()
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text('ADD_WORD', 'WELCOME_TEXT', user_lang),
                                 reply_markup=self.markup.get_cancel_markup())

        @self.dp.message_handler(state=DictionaryAddNewWordState.word)
        @self.analytics.fsm_metric
        async def new_word_state_word_handler(message: types.Message, state: FSMContext):
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            if re.match("^[A-Z]?[a-z]$", message.text):
                await message.answer(self.lang.get_page_text('ADD_WORD', 'NOT_VALID', user_lang))
                return
            async with state.proxy() as data:
                data['word'] = message.text
            await DictionaryAddNewWordState.next()
            await message.reply(self.lang.get_page_text('ADD_WORD', 'TRANSLATE_TEXT', user_lang))

        @self.dp.message_handler(state=DictionaryAddNewWordState.translation)
        @self.analytics.fsm_metric
        async def new_word_state_translation_handler(message: types.Message, state: FSMContext):
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            async with state.proxy() as data:
                data['translation'] = message.text
            await DictionaryAddNewWordState.next()
            await message.answer(self.lang.get_page_text('ADD_WORD', 'CONFIRMATION', user_lang) +
                                 f"\n\n{data['word']} - {data['translation']}",
                                 reply_markup=self.markup.get_confirmation_markup(user_lang))

        @self.dp.message_handler(state=DictionaryAddNewWordState.confirmation)
        @self.analytics.fsm_metric
        async def new_word_state_confirmation_handler(message: types.Message, state: FSMContext):
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            async with state.proxy() as data:
                confirmation_options = self.lang.get_markup_localization('ADD_WORD', user_lang)
                data['confirmation'] = message.text == confirmation_options[0]
            if data['confirmation']:
                self.db.add_user_word(data['word'], data['translation'], message['from']['id'], 'en', 'ru')
                msg = self.lang.get_page_text('ADD_WORD', 'SUCCESSFUL_ADDED', user_lang) + ':\n\n'
                msg += f"{data['word']} - {data['translation']}"
                await message.answer(msg, reply_markup=self.markup.get_dictionary_markup(user_lang))
            else:
                await message.answer(self.lang.get_page_text('ADD_WORD', 'CANCELLED', user_lang),
                                     reply_markup=self.markup.get_dictionary_markup(user_lang))
            await state.finish()
            await asyncio.sleep(1)
            await message.answer(text=self.lang.get_page_text('DICTIONARY', 'TEXT', user_lang),
                                 reply_markup=self.markup.get_dictionary_markup(user_lang))
            await message.answer(text=self.lang.get_user_dict(message['from']['id'], user_lang),
                                 reply_markup=self.markup.get_pagination_markup('dictionary')
                                 if (len(self.db.get_user_dict(message['from']['id'])) > 0) else None)

        # IF MAIN_MENU -> DELETE WORD COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[1])
        @self.analytics.default_metric
        async def delete_word_command_handler(message: types.Message):
            """TODO: Handler for delete word command (➖ Delete word)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await DictionaryDeleteWordState.search_query.set()
            await message.answer(text=self.lang.get_page_text('DELETE_WORD', 'WELCOME_TEXT', user_lang),
                                 reply_markup=self.markup.get_cancel_markup())

        @self.dp.message_handler(state=DictionaryDeleteWordState.search_query)
        @self.analytics.fsm_metric
        async def delete_word_state_search_query_handler(message: types.Message, state: FSMContext):
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            async with state.proxy() as data:
                data['search_query'] = message.text
                data['word_id'] = self.db.get_user_word_by_str(message.text, message['from']['id'])
            if data['word_id'] is not None:
                await DictionaryDeleteWordState.next()
                await message.answer(
                    self.lang.get_word_info(self.db.get_user_word_by_str(message.text, message['from']['id']),
                                            message['from']['id'], user_lang),
                    reply_markup=self.markup.get_confirmation_markup(user_lang))
            else:
                await state.finish()
                await message.answer(self.lang.get_page_text('DELETE_WORD', 'NOT_FOUND', user_lang))
                await message.answer(text=self.lang.get_page_text('DICTIONARY', 'TEXT', user_lang),
                                     reply_markup=self.markup.get_dictionary_markup(user_lang))
                await message.answer(text=self.lang.get_user_dict(message['from']['id'], user_lang),
                                     reply_markup=self.markup.get_pagination_markup('dictionary')
                                     if (len(self.db.get_user_dict(message['from']['id'])) > 0) else None)

        @self.dp.message_handler(state=DictionaryDeleteWordState.confirmation)
        @self.analytics.fsm_metric
        async def delete_word_state_confirmation_handler(message: types.Message, state: FSMContext):
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            confirmation_options = self.lang.get_markup_localization('ADD_WORD', user_lang)
            if message.text == confirmation_options[0]:
                async with state.proxy() as data:
                    self.db.delete_user_word(data['word_id'], message['from']['id'])
                await message.answer(self.lang.get_page_text('DELETE_WORD', 'SUCCESSFUL_DELETED', user_lang))
            else:
                await message.answer(self.lang.get_page_text('DELETE_WORD', 'CANCELLED', user_lang))
            await state.finish()
            await asyncio.sleep(1)
            await message.answer(text=self.lang.get_page_text('DICTIONARY', 'TEXT', user_lang),
                                 reply_markup=self.markup.get_dictionary_markup(user_lang))
            await message.answer(text=self.lang.get_user_dict(message['from']['id'], user_lang),
                                 reply_markup=self.markup.get_pagination_markup('dictionary')
                                 if (len(self.db.get_user_dict(message['from']['id'])) > 0) else None)

        # IF MAIN_MENU -> EDIT WORD COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[2])
        @self.analytics.default_metric
        async def edit_word_command_handler(message: types.Message):
            """TODO: Handler for edit word command (✏ Edit word)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await DictionaryEditWordState.search_query.set()
            await message.answer(text=self.lang.get_page_text('EDIT_WORD', 'WELCOME_TEXT', user_lang),
                                 reply_markup=self.markup.get_cancel_markup())

        @self.dp.message_handler(state=DictionaryEditWordState.search_query)
        @self.analytics.fsm_metric
        async def edit_word_state_search_query_handler(message: types.Message, state: FSMContext):
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            async with state.proxy() as data:
                data['search_query'] = message.text
            query_result = self.db.search_user_word(message['from']['id'], data['search_query'])
            if len(query_result) > 0:
                await message.answer(self.lang.get_page_text('EDIT_WORD', 'WORD_FOUND', user_lang) + '\n\n'
                                     + f'[{query_result[5]} - {query_result[6]}] {query_result[2]} - {query_result[3]}')

        # IF MAIN_MENU -> FIND WORD COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[3])
        @self.analytics.default_metric
        async def find_word_command_handler(message: types.Message):
            """Handler for edit word command (🔎 Find word)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await DictionarySearchWordState.search_query.set()
            await message.answer(text=self.lang.get_page_text('FIND_WORD', 'WELCOME_TEXT', user_lang),
                                 reply_markup=self.markup.get_cancel_markup())

        @self.dp.message_handler(state=DictionarySearchWordState.search_query)
        @self.analytics.fsm_metric
        async def search_word_state_search_query_handler(message: types.Message, state: FSMContext):
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            async with state.proxy() as data:
                data['search_query'] = message.text
            query_result = self.db.search_user_word(message['from']['id'], data['search_query'])
            if len(query_result) > 0:
                await message.answer(self.lang.get_page_text('FIND_WORD', 'WORD_FOUND', user_lang) + '\n\n'
                                     + str(query_result))
                async with state.proxy() as data:
                    data['result'] = query_result
                await DictionarySearchWordState.next()
            else:
                await state.finish()
                await message.answer(self.lang.get_page_text('FIND_WORD', 'NOT_FOUND', user_lang))

        @self.dp.message_handler(state=DictionarySearchWordState.confirmation)
        @self.analytics.fsm_metric
        async def search_word_state_confirmation_handler(message: types.Message, state: FSMContext):
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            ...

        # IF MAIN_MENU -> QUIZ COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[4])
        @self.analytics.default_metric
        async def quiz_command_handler(message: types.Message):
            """Handler for edit word command (📝 Quiz)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text('QUIZ', 'TEXT', user_lang),
                                 reply_markup=self.markup.get_quiz_start_markup(user_lang))

        # IF MAIN_MENU -> STATISTICS COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[5])
        @self.analytics.default_metric
        async def quiz_command_handler(message: types.Message):
            """Handler for edit word command (📉 Statistics)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            user_last_word_added = self.db.get_user_dict_last_word_date(message['from']['id'])
            await message.answer(text=self.lang.get_user_dict_stats_page(message['from']['id'],
                                                                         user_last_word_added.year,
                                                                         user_last_word_added.month,
                                                                         0, user_lang),
                                 reply_markup=self.markup.get_pagination_markup('statistics'),
                                 parse_mode="Markdown")

        @self.dp.message_handler(lambda message: message.text.startswith('/word_'))
        @self.analytics.default_metric
        async def word_by_id_command_handler(message: types.Message):
            word_id = int(message.text[6:])
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            if self.db.word_is_users(word_id, message['from']['id']):
                await message.answer(text=self.lang.get_word_info(word_id, message['from']['id'], user_lang))

        @self.dp.message_handler()
        @rate_limit(5, 'echo')
        @self.analytics.default_metric
        async def echo_message_handler(message: types.Message):
            """Default message handler for unrecognizable messages"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            logging.getLogger(type(self).__name__).info(f'ECHO [{message["from"]["id"]}] {message.text}')
            await message.answer(text=self.lang.get('ECHO_MESSAGE', user_lang))

    async def init_commands(self):
        """Init commands and their descriptions"""
        await self.bot.set_my_commands(self.commands)

    async def shutdown(self):
        """Operations for safely bot shutdown"""
        self.db.close_connection()
