# -*- coding: utf-8 -*-

# ===== Default imports =====

import logging

# ===== External libs imports =====

from aiogram import Dispatcher, types

# ===== Local imports =====

from analytics import BotAnalytics
from db_manager import DbManager
from lang_manager import LangManager
from markups_manager import MarkupManager


class VocabularyBotCallbackHandler:
    """Class for Vocabulary Bot callback handlers"""

    def __init__(self, db_manager: DbManager, lang_manager: LangManager, markup_manager: MarkupManager,
                 analytics: BotAnalytics, dispatcher: Dispatcher):
        self.db = db_manager
        self.lang = lang_manager
        self.markup = markup_manager
        self.analytics = analytics
        self.dp = dispatcher
        self.__init_handlers()

    def __init_handlers(self):
        # CALLBACK HANDLER FOR USER LANGUAGE SETTINGS
        @self.dp.callback_query_handler(lambda query: query.data.startswith('lang_setting_'))
        @self.analytics.callback_metric
        async def language_settings_callback_handler(query: types.CallbackQuery):
            """Handle selecting preferred interface language"""
            user_lang = self.lang.parse_user_lang(query['from']['id'])
            selected_lang = query['data'][-2:]
            if selected_lang != user_lang:
                self.db.set_user_lang(query['from']['id'], selected_lang)
                await query.message.delete()
                await query.message.answer(text=self.lang.get_page_text('LANG_SETTINGS', 'SUCCESS', selected_lang),
                                           reply_markup=self.markup.get_main_menu_markup(selected_lang))
                await query.message.answer(text=self.lang.get_page_text('SETTINGS', 'TEXT', selected_lang),
                                           reply_markup=self.markup.get_settings_markup(selected_lang))
                await query.answer()
            else:
                await query.answer(self.lang.get_page_text('LANG_SETTINGS', 'ERROR', user_lang), show_alert=True)

        @self.dp.callback_query_handler(lambda query: query.data.startswith('help_question_'))
        @self.analytics.callback_metric
        async def help_callback_handler(query: types.CallbackQuery):
            """Handle HELP page question buttons"""
            user_id = query['from']['id']
            user_lang = self.lang.parse_user_lang(user_id)
            question = query['data']
            await query.message.edit_text(self.lang.get_page_text("HELP", question, user_lang))
            await query.message.edit_reply_markup(self.markup.get_help_back_markup(user_lang))
            await query.answer()

        @self.dp.callback_query_handler(lambda query: query.data == 'back_to_help')
        @self.analytics.callback_metric
        async def back_to_help_callback_handler(query: types.CallbackQuery):
            """Handle HELP page question back button"""
            user_id = query['from']['id']
            user_lang = self.lang.parse_user_lang(user_id)
            await query.message.edit_text(self.lang.get_page_text("HELP", "TEXT", user_lang))
            await query.message.edit_reply_markup(self.markup.get_help_markup(user_lang))
            await query.answer()

        @self.dp.callback_query_handler(lambda query: query.data.startswith('settings_'))
        @self.analytics.callback_metric
        async def settings_page_callback_handler(query: types.CallbackQuery):
            """Handle SETTINGS page buttons"""
            user_id = query['from']['id']
            user_lang = self.lang.parse_user_lang(user_id)
            page = query['data'][9:]
            if page == 'interface':
                await query.message.edit_text(self.lang.get_page_text("LANG_SETTINGS", "TEXT", user_lang))
                await query.message.edit_reply_markup(self.markup.get_lang_settings_markup(user_lang))
                await query.answer()
            else:
                await query.answer('In developing...', show_alert=True)

        @self.dp.callback_query_handler(lambda query: query.data.startswith('first_'))
        @self.analytics.callback_metric
        async def pagination_first_callback_handler(query: types.CallbackQuery):
            action = query.data[6:]
            logging.getLogger(type(self).__name__).info(f'[{action}] callback executed.')
            await query.answer()

        @self.dp.callback_query_handler(lambda query: query.data.startswith('prev_'))
        @self.analytics.callback_metric
        async def pagination_prev_callback_handler(query: types.CallbackQuery):
            action = query.data[5:]
            logging.getLogger(type(self).__name__).info(f'[{action}] callback executed.')
            await query.answer()

        @self.dp.callback_query_handler(lambda query: query.data.startswith('next_'))
        @self.analytics.callback_metric
        async def pagination_next_callback_handler(query: types.CallbackQuery):
            action = query.data[5:]
            logging.getLogger(type(self).__name__).info(f'[{action}] callback executed.')
            await query.answer()

        @self.dp.callback_query_handler(lambda query: query.data.startswith('last_'))
        @self.analytics.callback_metric
        async def pagination_last_callback_handler(query: types.CallbackQuery):
            action = query.data[5:]
            logging.getLogger(type(self).__name__).info(f'[{action}] callback executed.')
            await query.answer()
