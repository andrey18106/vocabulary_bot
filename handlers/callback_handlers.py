# -*- coding: utf-8 -*-

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
        """TODO: Implement handlers"""
        self.db = db_manager
        self.lang = lang_manager
        self.markup = markup_manager
        self.analytics = analytics
        self.dp = dispatcher
        self.__init_handlers()

    def __init_handlers(self):
        """Initializing callback message handlers"""

        # CALLBACK HANDLER FOR USER LANGUAGE SETTINGS
        @self.dp.callback_query_handler(lambda query: query.data.startswith('lang_setting_'))
        @self.analytics.callback_metric
        async def language_settings_callback_handler(query: types.CallbackQuery):
            """Handle selecting preferred interface language"""
            user_lang = self.lang.parse_user_lang(query['from']['id'])
            user_id = query['from']['id']
            selected_lang = query['data'][-2:]
            if selected_lang != user_lang:
                self.db.set_user_lang(user_id, selected_lang)
                await query.message.delete()
                await query.message.answer(text=self.lang.get_page_text("LANG_SETTINGS", "SUCCESS", selected_lang),
                                           reply_markup=self.markup.get_main_menu_markup(selected_lang))
                await query.answer()
            else:
                await query.answer(self.lang.get_page_text('LANG_SETTINGS', 'ERROR', user_lang), show_alert=True)