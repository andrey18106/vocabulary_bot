# -*- coding: utf-8 -*-

# ===== Default imports =====

import logging

# ===== External libs imports =====

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext

# ===== Local imports =====

from analytics import BotAnalytics
from db_manager import DbManager
from lang_manager import LangManager
from markups_manager import MarkupManager
from states.Dictionary import DictionaryQuizState
from states.Mailing import AdminMailingState


class VocabularyBotCallbackHandler:
    """Class for Vocabulary Bot callback handlers"""

    def __init__(self, db_manager: DbManager, lang_manager: LangManager, markup_manager: MarkupManager,
                 analytics: BotAnalytics, dispatcher: Dispatcher, bot: Bot):
        self.db = db_manager
        self.lang = lang_manager
        self.markup = markup_manager
        self.analytics = analytics
        self.dp = dispatcher
        self.bot = bot
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
            elif page == 'newsletters':
                await query.message.edit_text(self.lang.get_page_text("NEWSLETTER_SETTINGS", "TEXT", user_lang))
                await query.message.edit_reply_markup(self.markup.get_news_settings_markup(user_lang))
                await query.answer()
            elif page == 'leo_import':
                await query.answer('Leo import is unavailable now. Keep waiting for it in the future', show_alert=True)

        @self.dp.callback_query_handler(lambda query: query.data.startswith('news_setting_'))
        @self.analytics.callback_metric
        async def language_settings_callback_handler(query: types.CallbackQuery):
            """Newsletters settings"""
            user_lang = self.lang.parse_user_lang(query['from']['id'])
            selected_option = query['data'][13:]
            if selected_option == 'all':
                self.db.set_user_mailings(query['from']['id'], 2)
            elif selected_option == 'important':
                self.db.set_user_mailings(query['from']['id'], 1)
            elif selected_option == 'disable':
                self.db.set_user_mailings(query['from']['id'], 0)
            await query.message.delete()
            await query.message.answer(self.lang.get_page_text("NEWSLETTER_SETTINGS", "SUCCESS", user_lang))
            await query.message.answer(text=self.lang.get_page_text('SETTINGS', 'TEXT', user_lang),
                                       reply_markup=self.markup.get_settings_markup(user_lang))

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

        @self.dp.callback_query_handler(lambda query: query.data == 'profile_referral_link')
        @self.analytics.callback_metric
        async def profile_referral_link_callback_handler(query: types.CallbackQuery):
            user_lang = self.lang.parse_user_lang(query['from']['id'])
            await query.message.answer(self.lang.get_user_referral_link_page(query['from']['id'], user_lang))
            await query.message.edit_reply_markup(None)
            await query.answer()

        @self.dp.callback_query_handler(lambda query: query.data.startswith('mailings_'))
        @self.analytics.callback_metric
        async def admin_mailings_new_callback_handler(query: types.CallbackQuery):
            user_lang = self.lang.parse_user_lang(query['from']['id'])
            action = query['data'][9:]
            if action == 'new':
                await AdminMailingState.message.set()
                await query.message.delete()
                await query.message.answer(text=self.lang.get_page_text('MAILINGS', 'NEW', user_lang),
                                           reply_markup=self.markup.get_cancel_markup())
            elif action == 'schedule_list':
                await query.answer()

        @self.dp.callback_query_handler(lambda query: query.data == 'quiz_start')
        @self.analytics.callback_fsm_metric
        async def quiz_start_callback_handler(query: types.CallbackQuery, state: FSMContext):
            await query.answer()
            await query.message.delete()
            user_lang = self.lang.parse_user_lang(query['from']['id'])
            quiz_data = self.db.get_user_quiz_data(query['from']['id'], 'en', 'ru')
            await DictionaryQuizState.user_answers.set()
            async with state.proxy() as data:
                data['quiz_results'] = []
                data['quiz_data'] = quiz_data
                data['index'] = 1
                await self.bot.send_poll(chat_id=query['from']['id'],
                                         question=self.lang.get_page_text('QUIZ', 'QUESTION', user_lang).format(
                                             quiz_data[0]['word']),
                                         options=quiz_data[0]['options'],
                                         correct_option_id=quiz_data[0]['options'].index(quiz_data[0]['answer']),
                                         type='quiz',
                                         reply_markup=self.markup.get_quiz_next_markup(user_lang))

        @self.dp.callback_query_handler(state=DictionaryQuizState.user_answers)
        @self.analytics.callback_fsm_metric
        async def quiz_next_callback_handler(query: types.CallbackQuery, state: FSMContext):
            user_lang = self.lang.parse_user_lang(query['from']['id'])
            if query.message.poll.total_voter_count == 1:
                await query.answer()
                await query.message.delete()
                async with state.proxy() as data:
                    curr_q_index = data['index']
                    quiz_result = {
                        'word': data['quiz_data'][curr_q_index - 1]['word'],
                        'selected_option': query.message.poll.options.index(
                            list(filter(lambda item: item.voter_count == 1,
                                        query.message.poll.options))[0]),
                        'correct_option': query.message.poll.correct_option_id,
                        'options': list(map(lambda item: dict(item), query.message.poll.options))
                    }
                    data['quiz_results'].append(quiz_result)
                    if curr_q_index < len(data['quiz_data']) - 1:
                        data['index'] = curr_q_index + 1
                    else:
                        await DictionaryQuizState.finish.set()
                    await self.bot.send_poll(chat_id=query['from']['id'],
                                             question=self.lang.get_page_text('QUIZ', 'QUESTION', user_lang).format(
                                                 data['quiz_data'][curr_q_index]['word']),
                                             options=data['quiz_data'][curr_q_index]['options'],
                                             correct_option_id=data['quiz_data'][curr_q_index]['options'].index(
                                                 data['quiz_data'][curr_q_index]['answer']),
                                             type='quiz',
                                             reply_markup=self.markup.get_quiz_next_markup(user_lang)
                                             if curr_q_index != len(data['quiz_data']) - 1 else
                                             self.markup.get_quiz_finish_markup(user_lang))
            else:
                await query.answer(self.lang.get_page_text('QUIZ', 'NON_SELECTED', user_lang),
                                   show_alert=True)

        @self.dp.callback_query_handler(state=DictionaryQuizState.finish)
        @self.analytics.callback_fsm_metric
        async def quiz_finish_callback_handler(query: types.CallbackQuery, state: FSMContext):
            """TODO: Add collecting quiz stats and motivational messages after passing quizzes"""
            user_lang = self.lang.parse_user_lang(query['from']['id'])
            if query.message.poll.total_voter_count == 1:
                await query.answer()
                await query.message.delete()
                async with state.proxy() as data:
                    quiz_result = {
                        'word': data['quiz_data'][data['index']]['word'],
                        'selected_option': query.message.poll.options.index(
                            list(filter(lambda item: item.voter_count == 1,
                                        query.message.poll.options))[0]),
                        'correct_option': query.message.poll.correct_option_id,
                        'options': list(map(lambda item: dict(item), query.message.poll.options))
                    }
                    data['quiz_results'].append(quiz_result)
                    await query.message.answer(self.lang.get_page_text('QUIZ', 'FINISH', user_lang))
                    await query.message.answer(self.lang.get_quiz_results_page(data['quiz_results'], user_lang),
                                               parse_mode='Markdown')
                await state.finish()
            else:
                await query.answer(self.lang.get_page_text('QUIZ', 'NON_SELECTED', user_lang),
                                   show_alert=True)
