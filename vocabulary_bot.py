# -*- coding: utf-8 -*-

# ===== Default imports =====

import asyncio
import logging
import re

# ===== External libs imports =====

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.types import BotCommand
from aiogram.utils import markdown
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# ===== Local imports =====

import config
from admin_manager import AdminManager
from analytics import BotAnalytics
from db_manager import DbManager
from callback_handlers import VocabularyBotCallbackHandler
from lang_manager import LangManager
from markups_manager import MarkupManager
from antiflood import VocabularyBotAntifloodMiddleware
from states.Dictionary import DictionaryState, DictionaryAddNewWordState, DictionaryDeleteWordState, \
    DictionarySearchWordState, DictionaryEditWordState
import pagination


class VocabularyBot:
    """Basic class for Vocabulary Bot necessary logics"""

    REFERRAL_REGEX = "^referral_[0-9]*$"
    EN_PHRASE_REGEX = "^([A-Z]?[a-z]*'?[a-z]*)(,?( |-)?,?([A-z]|[a-z]?([a-z]*)'?[a-z]*))*$"
    USERS_FOR_RATING_LIMIT = 10
    commands = [
        BotCommand(command='/start', description='Start the bot'),
        BotCommand(command='/help', description='Welcome message'),
        BotCommand(command='/settings', description='Bot settings'),
        BotCommand(command='/cancel', description='Cancel command executing'),
        BotCommand(command='/quote', description='Quote of the day'),
        BotCommand(command='/ping', description='Check the latency')
    ]

    def __init__(self, bot: Bot, dispatcher: Dispatcher, dev_mode: bool):
        self.bot = bot
        self.dp = dispatcher
        self.dev_mode = dev_mode

        self.db = DbManager(config.PATH_TO_DB, self.dev_mode)
        self.db.create_connection()
        self.lang = LangManager(config.PATH_TO_TRANSLATIONS, self.db)
        self.markup = MarkupManager(self.lang)
        self.analytics = BotAnalytics(self.db)
        self.admin = AdminManager(self.bot, self.db, self.lang, self.markup, self.dp, self.analytics)

        self.dp.middleware.setup(VocabularyBotAntifloodMiddleware(self.lang))

        self.callbacks = VocabularyBotCallbackHandler(self.db, self.lang, self.markup, self.analytics, self.dp,
                                                      self.bot)

        self.__init_handlers()

    def __init_handlers(self):
        """Initializing basic Vocabulary Bot message handlers"""

        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

        @self.dp.message_handler(commands=['start'])
        @VocabularyBotAntifloodMiddleware.rate_limit(5, 'start')
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
                if message.get_args() is not None and re.match(self.REFERRAL_REGEX, message.get_args()):
                    referrer_id = int(message.get_args()[9:])
                    # IF REFERRER EXISTS AND REFERRAL USER IS NOT EXISTS IN THE DATABASE
                    if self.db.is_user_exists(referrer_id) and message['from']['id'] != referrer_id:
                        self.db.update_referral_count(referrer_id)
                        self.db.set_user_referrer(message['from']['id'], referrer_id)
            await message.answer(text=self.lang.get('WELCOME_MESSAGE', user_lang),
                                 reply_markup=self.markup.get_main_menu_markup(user_lang))

        @self.dp.message_handler(commands=['help'])
        @VocabularyBotAntifloodMiddleware.rate_limit(3, 'help')
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
            await message.reply(self.lang.get_page_text("THROTTLING", "CANCELED", user_lang),
                                reply_markup=self.markup.get_main_menu_markup(user_lang))

        @self.dp.message_handler(state="*", commands=['quote'])
        @VocabularyBotAntifloodMiddleware.rate_limit(5, 'quote')
        @self.analytics.default_metric
        async def quote_command_handler(message: types.Message):
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            msg_header = f'*{self.lang.get_page_text("QUOTE", "TEXT", user_lang)}*\n\n'
            author = '\n\n© '
            response = requests.get(config.QUOTE_API_ENDPOINT, verify=False)
            if response.status_code == 200:
                quote = response.json()['quote']['body']
                author += response.json()['quote']['author']
                await message.answer(text=msg_header + markdown.italic(quote) + markdown.bold(author),
                                     parse_mode='Markdown')
            else:
                await message.answer(text=self.lang.get_page_text('QUOTE', 'ERROR', user_lang))

        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_page_text('BACK_MAIN_MENU', 'BUTTON', self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG)),
            state="*")
        @self.analytics.fsm_metric
        async def back_main_menu_command_handler(message: types.Message, state: FSMContext):
            """Back to main menu command handler"""
            await state.finish()
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text('BACK_MAIN_MENU', 'TEXT', user_lang),
                                 reply_markup=self.markup.get_main_menu_markup(user_lang))

        async def _send_dictionary_page(message: types.Message, user_lang: str, state: FSMContext):
            paginator = getattr(pagination, 'dictionary'.capitalize() + 'Paginator')(self.lang, self.db, self.markup,
                                                                                     message['from']['id'])
            await message.answer(text=self.lang.get_page_text('DICTIONARY', 'TEXT', user_lang),
                                 reply_markup=self.markup.get_dictionary_markup(user_lang))
            await message.answer(text=paginator.first_page(user_lang), reply_markup=paginator.get_reply_markup())
            async with state.proxy() as data:
                data['curr_pagination_page'] = 0
            await DictionaryState.dictionary.set()

        # IF MAIN_MENU -> DICTIONARY COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("MAIN_MENU", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[0],
            state="*")
        @self.analytics.fsm_metric
        async def dictionary_command_handler(message: types.Message, state: FSMContext):
            """Handler for dictionary command (📃 Dictionary)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await _send_dictionary_page(message, user_lang, state)

        # IF MAIN_MENU -> ACHIEVEMENTS COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("MAIN_MENU", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[1],
            state="*")
        @self.analytics.default_metric
        async def achievements_command_handler(message: types.Message):
            """TODO: Achievements page"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text("ACHIEVEMENTS", "TEXT", user_lang))
            await message.answer(text=self.lang.get_achievements_page(message['from']['id'], user_lang),
                                 reply_markup=self.markup.get_pagination_markup('achievements'))

        # IF MAIN_MENU -> RATING COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("MAIN_MENU", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[2],
            state="*")
        @self.analytics.default_metric
        async def rating_command_handler(message: types.Message):
            """TODO: Rating page"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            if len(self.db.get_rating_list(10, 0)) >= self.USERS_FOR_RATING_LIMIT:
                await message.answer(text=self.lang.get_rating_page(message['from']['id'], user_lang))
            else:
                await message.answer(text=self.lang.get_page_text("RATING", "NOT_AVAILABLE", user_lang))

        # IF MAIN_MENU -> PROFILE COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("MAIN_MENU", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[
                3],
            state="*")
        @self.analytics.default_metric
        async def profile_command_handler(message: types.Message):
            """Handler for settings command (🙎‍♂️Profile)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_user_profile_page(message['from']['id'], user_lang),
                                 parse_mode='Markdown',
                                 reply_markup=self.markup.get_profile_referral_markup(user_lang))

        # IF MAIN_MENU -> SETTINGS COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("MAIN_MENU", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[4],
            state="*")
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
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[5],
            state="*")
        @self.analytics.default_metric
        async def help_command_handler(message: types.Message):
            """Handler for settings command (❓ Help)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text('HELP', 'TEXT', user_lang),
                                 reply_markup=self.markup.get_help_markup(user_lang))

        # IF MAIN_MENU -> ADD WORD COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[0],
            state=DictionaryState.dictionary)
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
            if re.match(self.EN_PHRASE_REGEX, message.text) is None:
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
            await _send_dictionary_page(message, user_lang, state)

        # IF MAIN_MENU -> DELETE WORD COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[1],
            state=DictionaryState.dictionary)
        @self.analytics.default_metric
        async def delete_word_command_handler(message: types.Message):
            """Handler for delete word command (➖ Delete word)"""
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
                await _send_dictionary_page(message, user_lang, state)

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
            await _send_dictionary_page(message, user_lang, state)

        # IF MAIN_MENU -> EDIT WORD COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[2],
            state=DictionaryState.dictionary)
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
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[3],
            state=DictionaryState.dictionary)
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
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[4],
            state=DictionaryState.dictionary)
        @self.analytics.default_metric
        async def quiz_command_handler(message: types.Message):
            """Handler for edit word command (📝 Quiz)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text('QUIZ', 'TEXT', user_lang),
                                 reply_markup=self.markup.get_quiz_start_markup(user_lang))

        # IF MAIN_MENU -> STATISTICS COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[5],
            state=DictionaryState.dictionary)
        @self.analytics.fsm_metric
        async def quiz_command_handler(message: types.Message, state: FSMContext):
            """Handler for edit word command (📉 Statistics)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            async with state.proxy() as data:
                state_data = {
                    'current_year_index': 0,
                    'current_month_index': 0,
                    'current_month_page': 0,
                    'current_total_page': 0
                }
                data['curr_pagination_page'] = state_data
                paginator = getattr(pagination, 'statistics'.capitalize() + 'Paginator')(self.lang, self.db,
                                                                                         self.markup,
                                                                                         message['from']['id'],
                                                                                         current_page=state_data)
            await message.answer(text=paginator.first_page(user_lang),
                                 reply_markup=paginator.get_reply_markup(),
                                 parse_mode=paginator.get_parse_mode())

        @self.dp.message_handler(lambda message: message.text.startswith('/word_'), state="*")
        @self.analytics.default_metric
        async def word_by_id_command_handler(message: types.Message):
            word_id = int(message.text[6:])
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            if self.db.word_in_user_dict(word_id, message['from']['id']):
                await message.answer(text=self.lang.get_word_info(word_id, message['from']['id'], user_lang))

        @self.dp.message_handler()
        @VocabularyBotAntifloodMiddleware.rate_limit(5, 'echo')
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
