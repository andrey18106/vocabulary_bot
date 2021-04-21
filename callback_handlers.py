# -*- coding: utf-8 -*-

# ===== Default imports =====

import asyncio
import logging

# ===== External libs imports =====

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext

# ===== Local imports =====

from analytics import BotAnalytics
from db_manager import DbManager
from lang_manager import LangManager
from markups_manager import MarkupManager
from states.Dictionary import DictionaryQuizState, DictionaryState, DictionaryEditWordState, DictionarySearchWordState
from states.Mailing import AdminMailingState
import pagination


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

        @self.dp.callback_query_handler(lambda query: query.data.startswith('news_setting_'))
        @self.analytics.callback_metric
        async def language_settings_callback_handler(query: types.CallbackQuery):
            """Newsletters settings"""
            user_lang = self.lang.parse_user_lang(query['from']['id'])
            selected_option = query['data'][13:]
            user_mailings = self.db.get_user_mailings(query['from']['id'])
            mailings_settings = ['disable', 'important', 'all']
            if mailings_settings[user_mailings] != selected_option:
                if selected_option == 'all' and user_mailings != 2:
                    self.db.set_user_mailings(query['from']['id'], 2)
                elif selected_option == 'important' and user_mailings != 1:
                    self.db.set_user_mailings(query['from']['id'], 1)
                elif selected_option == 'disable' and user_mailings != 0:
                    self.db.set_user_mailings(query['from']['id'], 0)
                await query.message.delete()
                await query.message.answer(self.lang.get_page_text("NEWSLETTER_SETTINGS", "SUCCESS", user_lang))
            else:
                await query.answer(self.lang.get_page_text('NEWSLETTER_SETTINGS', 'ALREADY_SET', user_lang),
                                   show_alert=True)

        async def _send_dictionary_page(message: types.Message, user_id: int, user_lang: str, from_lang: str,
                                        to_lang: str, state: FSMContext):
            current_state = {
                'current_page': 0,
                'from_lang': from_lang,
                'to_lang': to_lang
            }
            paginator = getattr(pagination, 'dictionary'.capitalize() + 'Paginator')(self.lang, self.db, self.markup,
                                                                                     user_id,
                                                                                     current_page=current_state)
            await message.answer(text=self.lang.get_page_text('DICTIONARY', 'TEXT', user_lang),
                                 reply_markup=self.markup.get_dictionary_markup(user_lang))
            await message.answer(text=paginator.first_page(user_lang), reply_markup=paginator.get_reply_markup())
            async with state.proxy() as data:
                data['curr_pagination_page'] = current_state
            await DictionaryState.dictionary.set()

        @self.dp.callback_query_handler(lambda query: query.data.startswith('dictionary_'), state="*")
        @self.analytics.callback_fsm_metric
        async def dictionary_list_callback_handler(query: types.CallbackQuery, state: FSMContext):
            user_lang = self.lang.parse_user_lang(query['from']['id'])
            selected_dict_pairs = query.data[11:].split('_')
            from_lang = selected_dict_pairs[0]
            to_lang = selected_dict_pairs[1]
            await query.message.delete()
            await _send_dictionary_page(query.message, query['from']['id'], user_lang, from_lang, to_lang, state)

        # PAGINATION
        @self.dp.callback_query_handler(lambda query: query.data.startswith('first_'), state="*")
        @self.analytics.callback_fsm_metric
        async def pagination_first_callback_handler(query: types.CallbackQuery, state: FSMContext):
            action = query.data[6:]
            user_lang = self.lang.parse_user_lang(query['from']['id'])
            async with state.proxy() as data:
                if 'curr_pagination_page' in data:
                    current_page = data['curr_pagination_page']
                    paginator = getattr(pagination, action.capitalize() + 'Paginator')(self.lang, self.db, self.markup,
                                                                                       query['from']['id'],
                                                                                       current_page=current_page)
                    if not paginator.is_first():
                        await query.message.edit_text(text=paginator.first_page(user_lang),
                                                      reply_markup=paginator.get_reply_markup(),
                                                      parse_mode=paginator.get_parse_mode())
                        data['curr_pagination_page'] = paginator.get_state_data()
                    else:
                        await query.answer(self.lang.get_page_text('PAGINATION', 'FIRST_REACHED', user_lang),
                                           show_alert=True)
            logging.getLogger(type(self).__name__).info(f'[{action}] callback executed.')
            await query.answer()

        @self.dp.callback_query_handler(lambda query: query.data.startswith('prev_'), state="*")
        @self.analytics.callback_fsm_metric
        async def pagination_prev_callback_handler(query: types.CallbackQuery, state: FSMContext):
            action = query.data[5:]
            user_lang = self.lang.parse_user_lang(query['from']['id'])
            async with state.proxy() as data:
                if 'curr_pagination_page' in data:
                    current_page = data['curr_pagination_page']
                    paginator = getattr(pagination, action.capitalize() + 'Paginator')(self.lang, self.db, self.markup,
                                                                                       query['from']['id'],
                                                                                       current_page=current_page)
                    if not paginator.is_first():
                        await query.message.edit_text(text=paginator.prev_page(user_lang),
                                                      reply_markup=paginator.get_reply_markup(),
                                                      parse_mode=paginator.get_parse_mode())
                        data['curr_pagination_page'] = paginator.get_state_data()
                    else:
                        await query.answer(self.lang.get_page_text('PAGINATION', 'FIRST_REACHED', user_lang),
                                           show_alert=True)
            logging.getLogger(type(self).__name__).info(f'[{action}] callback executed.')
            await query.answer()

        @self.dp.callback_query_handler(lambda query: query.data.startswith('next_'), state="*")
        @self.analytics.callback_fsm_metric
        async def pagination_next_callback_handler(query: types.CallbackQuery, state: FSMContext):
            action = query.data[5:]
            user_lang = self.lang.parse_user_lang(query['from']['id'])
            async with state.proxy() as data:
                if 'curr_pagination_page' in data:
                    current_page = data['curr_pagination_page']
                    paginator = getattr(pagination, action.capitalize() + 'Paginator')(self.lang, self.db, self.markup,
                                                                                       query['from']['id'],
                                                                                       current_page=current_page)
                    if not paginator.is_last():
                        await query.message.edit_text(text=paginator.next_page(user_lang),
                                                      reply_markup=paginator.get_reply_markup(),
                                                      parse_mode=paginator.get_parse_mode())
                        data['curr_pagination_page'] = paginator.get_state_data()
                    else:
                        await query.answer(self.lang.get_page_text('PAGINATION', 'LAST_REACHED', user_lang),
                                           show_alert=True)
            logging.getLogger(type(self).__name__).info(f'[{action}] callback executed.')
            await query.answer()

        @self.dp.callback_query_handler(lambda query: query.data.startswith('last_'), state="*")
        @self.analytics.callback_fsm_metric
        async def pagination_last_callback_handler(query: types.CallbackQuery, state: FSMContext):
            action = query.data[5:]
            user_lang = self.lang.parse_user_lang(query['from']['id'])
            async with state.proxy() as data:
                if 'curr_pagination_page' in data:
                    current_page = data['curr_pagination_page']
                    paginator = getattr(pagination, action.capitalize() + 'Paginator')(self.lang, self.db, self.markup,
                                                                                       query['from']['id'],
                                                                                       current_page=current_page)
                    if not paginator.is_last():
                        await query.message.edit_text(text=paginator.last_page(user_lang),
                                                      reply_markup=paginator.get_reply_markup(),
                                                      parse_mode=paginator.get_parse_mode())
                        data['curr_pagination_page'] = paginator.get_state_data()
                    else:
                        await query.answer(self.lang.get_page_text('PAGINATION', 'LAST_REACHED', user_lang),
                                           show_alert=True)
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

        # QUIZ CALLBACKS
        @self.dp.callback_query_handler(lambda query: query.data == 'quiz_start', state="*")
        @self.analytics.callback_fsm_metric
        async def quiz_start_callback_handler(query: types.CallbackQuery, state: FSMContext):
            await query.answer()
            await query.message.delete()
            user_lang = self.lang.parse_user_lang(query['from']['id'])
            async with state.proxy() as data:
                from_lang = data['curr_pagination_page']['from_lang']
                to_lang = data['curr_pagination_page']['to_lang']
            quiz_data = self.db.get_user_quiz_data(query['from']['id'], from_lang, to_lang, 10)
            await DictionaryQuizState.user_answers.set()
            async with state.proxy() as data:
                data['quiz_results'] = []
                data['quiz_data'] = quiz_data
                data['index'] = 1
                question = f"{data['index']}/{len(data['quiz_data'])} " + \
                           self.lang.get_page_text('QUIZ', 'QUESTION', user_lang).format(quiz_data[0]['word'])
                await self.bot.send_poll(chat_id=query['from']['id'],
                                         question=question,
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
                        question = f"{data['index']}/{len(data['quiz_data'])} "
                    else:
                        question = f"{len(data['quiz_data'])}/{len(data['quiz_data'])} "
                        await DictionaryQuizState.finish.set()
                    question += self.lang.get_page_text('QUIZ', 'QUESTION', user_lang).format(
                        data['quiz_data'][curr_q_index]['word'])
                    await self.bot.send_poll(chat_id=query['from']['id'],
                                             question=question,
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
                    last_pagination_page = data['curr_pagination_page']
                await state.finish()
                await DictionaryState.dictionary.set()
                async with state.proxy() as data:
                    data['curr_pagination_page'] = last_pagination_page
            else:
                await query.answer(self.lang.get_page_text('QUIZ', 'NON_SELECTED', user_lang),
                                   show_alert=True)

        @self.dp.callback_query_handler(state=DictionarySearchWordState.search_query)
        @self.analytics.callback_fsm_metric
        async def search_word_actions_callback_handler(query: types.CallbackQuery, state: FSMContext):
            user_lang = self.lang.parse_user_lang(query['from']['id'])
            action = query.data[10:]
            if action == 'add':
                async with state.proxy() as data:
                    new_word_string = data['search_query']
                    new_word_translation = data['translation']
                    from_lang = data['curr_pagination_page']['from_lang']
                    to_lang = data['curr_pagination_page']['to_lang']
                    self.db.add_user_word(new_word_string, new_word_translation, query['from']['id'], from_lang,
                                          to_lang)
                    await query.message.edit_text(self.lang.get_page_text('ADD_WORD', 'SUCCESSFUL_ADDED', user_lang))
                await state.finish()
                await asyncio.sleep(1)
                await _send_dictionary_page(query.message, query['from']['id'], user_lang, from_lang, to_lang, state)
            elif action == 'find_another':
                await query.message.delete()
                await query.message.answer(text=self.lang.get_page_text('FIND_WORD', 'WELCOME_TEXT', user_lang),
                                           reply_markup=self.markup.get_cancel_markup())

        @self.dp.callback_query_handler(state=DictionaryEditWordState.search_query)
        @self.analytics.callback_metric
        async def edit_word_actions_callback_handler(query: types.CallbackQuery):
            user_lang = self.lang.parse_user_lang(query['from']['id'])
            action = query.data[10:]
            if action == 'string':
                await DictionaryEditWordState.new_word_string.set()
                await query.message.delete()
                await query.message.answer(text=self.lang.get_page_text('EDIT_WORD', 'NEW_STRING', user_lang),
                                           reply_markup=self.markup.get_cancel_markup())
            elif action == 'translation':
                await DictionaryEditWordState.new_word_translation.set()
                await query.message.delete()
                await query.message.answer(text=self.lang.get_page_text('EDIT_WORD', 'NEW_TRANSLATION', user_lang),
                                           reply_markup=self.markup.get_cancel_markup())
