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
import translation


class VocabularyBot:
    """Basic class for Vocabulary Bot necessary logics"""

    REFERRAL_REGEX = "^referral_[0-9]*$"
    EN_PHRASE_REGEX = "^([A-Z]?[a-z]*'?[a-z]*)(,?( |-)?,?([A-z]|[a-z]?([a-z]*)'?[a-z]*))*$"
    USERS_FOR_RATING_LIMIT = 10
    commands = [
        BotCommand(command='/start', description='Start the bot'),
        BotCommand(command='/help', description='How to user'),
        BotCommand(command='/settings', description='Bot settings'),
        BotCommand(command='/cancel', description='Cancel command executing'),
        BotCommand(command='/quote', description='Quote of the day')
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

        async def _send_dictionary_page(message: types.Message, user_lang: str, from_lang: str, to_lang: str,
                                        state: FSMContext):
            current_state = {
                'current_page': 0,
                'from_lang': from_lang,
                'to_lang': to_lang
            }
            paginator = getattr(pagination, 'dictionary'.capitalize() + 'Paginator')(self.lang, self.db, self.markup,
                                                                                     message['from']['id'],
                                                                                     current_page=current_state)
            await message.answer(text=self.lang.get_page_text('DICTIONARY', 'TEXT', user_lang),
                                 reply_markup=self.markup.get_dictionary_markup(user_lang))
            await message.answer(text=paginator.first_page(user_lang), reply_markup=paginator.get_reply_markup())
            async with state.proxy() as data:
                data['curr_pagination_page'] = current_state
            await DictionaryState.dictionary.set()

        # IF MAIN_MENU -> DICTIONARY COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("MAIN_MENU", self.db.get_user_lang(
                message['from']['id']))[0], state="*")
        @self.analytics.default_metric
        async def dictionary_command_handler(message: types.Message):
            """Handler for dictionary command (📃 Dictionary)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(self.lang.get_page_text('DICTIONARY', 'LIST_TEXT', user_lang),
                                 reply_markup=self.markup.get_dictionary_list_markup(user_lang))

        # IF MAIN_MENU -> ACHIEVEMENTS COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("MAIN_MENU", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[1],
            state="*")
        @self.analytics.default_metric
        async def achievements_command_handler(message: types.Message):
            """TODO: Achievements page"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.answer(text=self.lang.get_page_text("ACHIEVEMENTS", "IN_DEVELOPING", user_lang))

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

        # IF MAIN_MENU -> DICTIONARY -> ADD WORD COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[0],
            state=DictionaryState.dictionary)
        @self.analytics.default_metric
        async def new_word_command_handler(message: types.Message):
            """Handler for add new word command (➕ Add word)"""
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
            elif self.db.get_user_word_by_str(message.text, message['from']['id']) is not None:
                await message.answer(self.lang.get_page_text('ADD_WORD', 'ALREADY_EXISTS', user_lang))
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
                from_lang = data['curr_pagination_page']['from_lang']
                to_lang = data['curr_pagination_page']['to_lang']
            if data['confirmation']:
                self.db.add_user_word(data['word'], data['translation'], message['from']['id'], from_lang, to_lang)
                msg = self.lang.get_page_text('ADD_WORD', 'SUCCESSFUL_ADDED', user_lang) + ':\n\n'
                msg += f"{data['word']} - {data['translation']}"
                await message.answer(msg, reply_markup=self.markup.get_dictionary_markup(user_lang))
            else:
                await message.answer(self.lang.get_page_text('ADD_WORD', 'CANCELLED', user_lang),
                                     reply_markup=self.markup.get_dictionary_markup(user_lang))
            await state.finish()
            await asyncio.sleep(1)
            await _send_dictionary_page(message, user_lang, from_lang, to_lang, state)

        # IF MAIN_MENU -> DICTIONARY -> DELETE WORD COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[1],
            state=DictionaryState.dictionary)
        @self.analytics.fsm_metric
        async def delete_word_command_handler(message: types.Message, state: FSMContext):
            """Handler for delete word command (➖ Delete word)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            async with state.proxy() as data:
                from_lang = data['curr_pagination_page']['from_lang']
                to_lang = data['curr_pagination_page']['to_lang']
            if self.db.get_user_dict_capacity(message['from']['id'], from_lang, to_lang) > 0:
                await DictionaryDeleteWordState.search_query.set()
                await message.answer(text=self.lang.get_page_text('DELETE_WORD', 'WELCOME_TEXT', user_lang),
                                     reply_markup=self.markup.get_cancel_markup())
            else:
                await message.answer(self.lang.get_page_text('DELETE_WORD', 'EMPTY_DICT', user_lang))

        @self.dp.message_handler(state=DictionaryDeleteWordState.search_query)
        @self.analytics.fsm_metric
        async def delete_word_state_search_query_handler(message: types.Message, state: FSMContext):
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            async with state.proxy() as data:
                data['search_query'] = message.text
                data['word_id'] = self.db.get_user_word_by_str(message.text, message['from']['id'])
                from_lang = data['curr_pagination_page']['from_lang']
                to_lang = data['curr_pagination_page']['to_lang']
            if data['word_id'] is not None:
                await DictionaryDeleteWordState.next()
                msg = self.lang.get_word_info(self.db.get_user_word_by_str(message.text, message['from']['id']),
                                              message['from']['id'], user_lang)
                msg += '\n\n' + self.lang.get_page_text('DELETE_WORD', 'CONFIRMATION', user_lang)
                await message.answer(text=msg,
                                     reply_markup=self.markup.get_confirmation_markup(user_lang))
            else:
                await state.finish()
                await message.answer(self.lang.get_page_text('DELETE_WORD', 'NOT_FOUND', user_lang))
                await _send_dictionary_page(message, user_lang, from_lang, to_lang, state)

        @self.dp.message_handler(state=DictionaryDeleteWordState.confirmation)
        @self.analytics.fsm_metric
        async def delete_word_state_confirmation_handler(message: types.Message, state: FSMContext):
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            confirmation_options = self.lang.get_markup_localization('ADD_WORD', user_lang)
            if message.text == confirmation_options[0]:
                async with state.proxy() as data:
                    self.db.delete_user_word(data['word_id'], message['from']['id'])
                    from_lang = data['curr_pagination_page']['from_lang']
                    to_lang = data['curr_pagination_page']['to_lang']
                await message.answer(self.lang.get_page_text('DELETE_WORD', 'SUCCESSFUL_DELETED', user_lang))
            else:
                await message.answer(self.lang.get_page_text('DELETE_WORD', 'CANCELLED', user_lang))
            await state.finish()
            await asyncio.sleep(1)
            await _send_dictionary_page(message, user_lang, from_lang, to_lang, state)

        # IF MAIN_MENU -> DICTIONARY -> EDIT WORD COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[2],
            state=DictionaryState.dictionary)
        @self.analytics.fsm_metric
        async def edit_word_command_handler(message: types.Message, state: FSMContext):
            """Handler for edit word command (✏ Edit word)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            async with state.proxy() as data:
                from_lang = data['curr_pagination_page']['from_lang']
                to_lang = data['curr_pagination_page']['to_lang']
            if self.db.get_user_dict_capacity(message['from']['id'], from_lang, to_lang) > 0:
                await DictionaryEditWordState.search_query.set()
                await message.answer(text=self.lang.get_page_text('EDIT_WORD', 'WELCOME_TEXT', user_lang),
                                     reply_markup=self.markup.get_cancel_markup())
            else:
                await message.answer(self.lang.get_page_text('EDIT_WORD', 'EMPTY_DICT', user_lang))

        @self.dp.message_handler(state=DictionaryEditWordState.search_query)
        @self.analytics.fsm_metric
        async def edit_word_state_search_query_handler(message: types.Message, state: FSMContext):
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            async with state.proxy() as data:
                data['search_query'] = message.text
            query_result = self.db.search_user_word(message['from']['id'], data['search_query'])
            if len(query_result) > 0:
                async with state.proxy() as data:
                    data['found_word'] = query_result
                await message.answer(self.lang.get_page_text('EDIT_WORD', 'WORD_FOUND', user_lang) + '\n\n'
                                     + f'[{query_result[5]} - {query_result[6]}] {query_result[2]} - {query_result[3]}',
                                     reply_markup=self.markup.get_edit_markup(user_lang))
            else:
                await message.answer(self.lang.get_page_text('EDIT_WORD', 'NOT_FOUND', user_lang))

        @self.dp.message_handler(state=DictionaryEditWordState.new_word_string)
        @self.analytics.fsm_metric
        async def edit_word_state_new_word_string_handler(message: types.Message, state: FSMContext):
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            async with state.proxy() as data:
                data['action'] = 'string'
                data['new_value'] = message.text
                msg = self.lang.get_page_text('EDIT_WORD', 'CONFIRMATION', user_lang) + ':\n\n'
                msg += f"{data['found_word'][2]} -> {data['new_value']}"
                await message.answer(text=msg, reply_markup=self.markup.get_confirmation_markup(user_lang))
                await DictionaryEditWordState.confirmation.set()

        @self.dp.message_handler(state=DictionaryEditWordState.new_word_translation)
        @self.analytics.fsm_metric
        async def edit_word_state_new_word_translation_handler(message: types.Message, state: FSMContext):
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            async with state.proxy() as data:
                data['action'] = 'translation'
                data['new_value'] = message.text
                msg = self.lang.get_page_text('EDIT_WORD', 'CONFIRMATION', user_lang) + ':\n\n'
                msg += f"{data['found_word'][3]} -> {data['new_value']}"
                await message.answer(text=msg, reply_markup=self.markup.get_confirmation_markup(user_lang))
                await DictionaryEditWordState.confirmation.set()

        @self.dp.message_handler(state=DictionaryEditWordState.confirmation)
        @self.analytics.fsm_metric
        async def edit_word_state_confirmation_handler(message: types.Message, state: FSMContext):
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            confirmation_options = self.lang.get_markup_localization('ADD_WORD', user_lang)
            async with state.proxy() as data:
                from_lang = data['curr_pagination_page']['from_lang']
                to_lang = data['curr_pagination_page']['to_lang']
            if message.text == confirmation_options[0]:
                async with state.proxy() as data:
                    word_id = data['found_word'][0]
                    if data['action'] == 'string':
                        self.db.update_user_word_string(message['from']['id'], word_id, data['new_value'])
                    elif data['action'] == 'translation':
                        self.db.update_user_word_translation(message['from']['id'], word_id, data['new_value'])
                    await message.answer(self.lang.get_page_text('EDIT_WORD', 'SUCCESSFUL', user_lang))
                    await state.finish()
                    await DictionaryState.dictionary.set()
                    await _send_dictionary_page(message, user_lang, from_lang, to_lang, state)
            else:
                await message.answer(self.lang.get_page_text('EDIT_WORD', 'CANCELED', user_lang))
                await state.finish()
                await _send_dictionary_page(message, user_lang, from_lang, to_lang, state)

        # IF MAIN_MENU -> DICTIONARY -> FIND WORD COMMAND
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
                from_lang = data['curr_pagination_page']['from_lang']
                to_lang = data['curr_pagination_page']['to_lang']
            query_result = self.db.search_user_word(message['from']['id'], data['search_query'])
            if len(query_result) > 0:
                found_word_str = f"[{query_result[5]} - {query_result[6]}] " \
                                 f"{query_result[2]} - {query_result[3]} /word_{query_result[0]}"
                await message.answer(self.lang.get_page_text('FIND_WORD', 'WORD_FOUND', user_lang) + '\n\n'
                                     + found_word_str)
                async with state.proxy() as data:
                    data['result'] = query_result
                await state.finish()
                await _send_dictionary_page(message, user_lang, from_lang, to_lang, state)
            else:
                word_translation = translation.linguee_translate(data['search_query'])
                async with state.proxy() as data:
                    data['translation'] = word_translation
                msg = f"{self.lang.get_page_text('FIND_WORD', 'NOT_FOUND', user_lang)}\n"
                msg += f"{self.lang.get_page_text('FIND_WORD', 'NOT_FOUND_TRANSLATION', user_lang)}:\n\n"
                msg += f"{data['search_query']} - {word_translation}"
                await message.answer(text=msg, reply_markup=self.markup.get_find_word_found_markup(user_lang))

        # IF MAIN_MENU -> DICTIONARY -> QUIZ COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                message['from']['id'] if self.db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[4],
            state=DictionaryState.dictionary)
        @self.analytics.fsm_metric
        async def quiz_command_handler(message: types.Message, state: FSMContext):
            """Handler for edit word command (📝 Quiz)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            async with state.proxy() as data:
                from_lang = data['curr_pagination_page']['from_lang']
                to_lang = data['curr_pagination_page']['to_lang']
            if self.db.get_user_dict_capacity(message['from']['id'], from_lang, to_lang) > 10:
                await message.answer(text=self.lang.get_page_text('QUIZ', 'TEXT', user_lang),
                                     reply_markup=self.markup.get_quiz_start_markup(user_lang))
            else:
                await message.answer(self.lang.get_page_text('QUIZ', 'NOT_ENOUGH_DATA', user_lang))

        # IF MAIN_MENU -> DICTIONARY -> STATISTICS COMMAND
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
                    'current_total_page': 0,
                    'from_lang': data['curr_pagination_page']['from_lang'],
                    'to_lang': data['curr_pagination_page']['to_lang']
                }
                data['curr_pagination_page'] = state_data
                paginator = getattr(pagination, 'statistics'.capitalize() + 'Paginator')(self.lang, self.db,
                                                                                         self.markup,
                                                                                         message['from']['id'],
                                                                                         current_page=state_data)
            if self.db.get_user_dict_capacity(message['from']['id'], state_data['from_lang'],
                                              state_data['to_lang']) > 0:
                await message.answer(text=paginator.first_page(user_lang),
                                     reply_markup=paginator.get_reply_markup(),
                                     parse_mode=paginator.get_parse_mode())
            else:
                await message.answer(self.lang.get_page_text('DICT_STATS', 'NOT_ENOUGH_DATA', user_lang))

        # IF MAIN_MENU -> DICTIONARY -> LIST COMMAND
        @self.dp.message_handler(
            lambda message: message.text == self.lang.get_markup_localization("DICTIONARY", self.db.get_user_lang(
                                message['from']['id'] if self.db.is_user_exists(
                                    message['from']['id']) else config.DEFAULT_LANG))[6],
            state=DictionaryState.dictionary)
        @self.analytics.fsm_metric
        async def dictionary_list_words_command_handler(message: types.Message, state: FSMContext):
            """Handler for edit word command (📃 List words)"""
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            async with state.proxy() as data:
                from_lang = data['curr_pagination_page']['from_lang']
                to_lang = data['curr_pagination_page']['to_lang']
                await _send_dictionary_page(message, user_lang, from_lang, to_lang, state)

        @self.dp.message_handler(lambda message: message.text.startswith('/word_'), state="*")
        @self.analytics.default_metric
        async def word_by_id_command_handler(message: types.Message):
            """TODO: Add InlineKeyboardMarkup for additional actions with word (audio, definitions, etc.)"""
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

    async def run_scheduler(self):
        """Run Vocabulary Bot Task Scheduler for regular jobs."""
        pass

    async def shutdown(self):
        """Operations for safely bot shutdown"""
        self.db.close_connection()
