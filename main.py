# -*- coding: utf-8 -*-

# TODO: Add antiflood middleware
# TODO: Try to change polling to webhook on local server just for performance tests
# TODO: Learn handling bot unique links for some actions (like referral links)
# TODO: Learn how to improve performance (throttling examples)
# TODO: Create mechanism for mass messaging (newsletter)
# TODO: Along with mass messaging mechanism implement the daily(or weakly) personal quizzes for all users (+settings)
# TODO: After implementing basic functions (Add, Delete, Edit, Find) - test spell checking ready solutions

# ===== Default imports =====

import logging

# ===== External libs imports =====

from aiogram import Bot, Dispatcher, executor, types

# ===== Local imports =====

import config
from analytics import BotAnalytics
from db_manager import DbManager
from lang_manager import LangManager
from markups_manager import MarkupManager

# ===== Basic initializations =====

logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.TOKEN)
dp = Dispatcher(bot)

db = DbManager(config.PATH_TO_DB)
db.create_connection()

lang = LangManager(config.PATH_TO_TRANSLATIONS, db)
markup = MarkupManager(lang)
analytics = BotAnalytics(db)


# ===== Message Handlers =====

@dp.message_handler(commands=['start', 'help'])
@analytics.default_metric
async def welcome_message_handler(message: types.Message):
    """`/start` and `/help`commands handler"""
    if db.is_user_exists(message['from']['id']):
        user_lang = db.get_user_lang(message['from']['id'])
    else:
        db.add_user(message['from']['id'], message['from']['username'], message['from']['first_name'],
                    message['from']['last_name'])
        db.set_user_lang(message['from']['id'], config.DEFAULT_LANG)
        user_lang = config.DEFAULT_LANG
    await message.answer(text=lang.get('WELCOME_MESSAGE', user_lang),
                         reply_markup=markup.get_main_menu_markup(user_lang))


# IF MAIN_MENU -> ADD WORD COMMAND
@dp.message_handler(lambda message: message.text == lang.get_markup_localization("MAIN_MENU", db.get_user_lang(
    message['from']['id'] if db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[0])
@analytics.default_metric
async def new_word_command_handler(message: types.Message):
    """Handler for add new word command (➕ Add word)"""
    user_lang = lang.parse_user_lang(message['from']['id'])
    await message.answer(text=lang.get('ECHO_MESSAGE', user_lang))


# IF MAIN_MENU -> DELETE WORD COMMAND
@dp.message_handler(lambda message: message.text == lang.get_markup_localization("MAIN_MENU", db.get_user_lang(
    message['from']['id'] if db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[1])
@analytics.default_metric
async def delete_word_command_handler(message: types.Message):
    """TODO: Handler for delete word command (➖ Delete word)"""
    user_lang = lang.parse_user_lang(message['from']['id'])
    await message.answer(text=lang.get('ECHO_MESSAGE', user_lang))


# IF MAIN_MENU -> EDIT WORD COMMAND
@dp.message_handler(lambda message: message.text == lang.get_markup_localization("MAIN_MENU", db.get_user_lang(
    message['from']['id'] if db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[2])
@analytics.default_metric
async def edit_word_command_handler(message: types.Message):
    """TODO: Handler for edit word command (✏ Edit word)"""
    user_lang = lang.parse_user_lang(message['from']['id'])
    await message.answer(text=lang.get('ECHO_MESSAGE', user_lang))


# IF MAIN_MENU -> DICTIONARY COMMAND
@dp.message_handler(lambda message: message.text == lang.get_markup_localization("MAIN_MENU", db.get_user_lang(
    message['from']['id'] if db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[3])
@analytics.default_metric
async def dictionary_command_handler(message: types.Message):
    """TODO: Handler for dictionary command (📃 Dictionary)"""
    user_lang = lang.parse_user_lang(message['from']['id'])
    await message.answer(text=lang.get('ECHO_MESSAGE', user_lang))


# IF MAIN_MENU -> SETTINGS COMMAND
@dp.message_handler(lambda message: message.text == lang.get_markup_localization("MAIN_MENU", db.get_user_lang(
    message['from']['id'] if db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[4])
@analytics.default_metric
async def settings_command_handler(message: types.Message):
    """Handler for settings command (⚙ Settings)"""
    user_lang = lang.parse_user_lang(message['from']['id'])
    await message.answer(text=lang.get_lang_settings_text("LANG_SETTINGS", "TEXT", user_lang),
                         reply_markup=markup.get_lang_settings_markup(user_lang))


# IF MAIN_MENU -> HELP COMMAND
@dp.message_handler(lambda message: message.text == lang.get_markup_localization("MAIN_MENU", db.get_user_lang(
    message['from']['id'] if db.is_user_exists(message['from']['id']) else config.DEFAULT_LANG))[5])
@analytics.default_metric
async def settings_command_handler(message: types.Message):
    """Handler for settings command (❓ Help)"""
    user_lang = lang.parse_user_lang(message['from']['id'])
    await message.answer(text=lang.get_lang_settings_text("LANG_SETTINGS", "TEXT", user_lang),
                         reply_markup=markup.get_lang_settings_markup(user_lang))


@dp.message_handler()
@analytics.default_metric
async def echo_message_handler(message: types.Message):
    """Default message handler for unrecognizable messages"""
    user_lang = lang.parse_user_lang(message['from']['id'])
    await message.answer(text=lang.get('ECHO_MESSAGE', user_lang))


# ===== Callback Handlers =====

# CALLBACK HANDLER FOR USER LANGUAGE SETTINGS
@dp.callback_query_handler(lambda query: query.data.startswith('lang_setting_'))
@analytics.callback_metric
async def language_settings_callback_handler(query: types.CallbackQuery):
    """Handle selecting preferred interface language"""
    user_id = query['from']['id']
    selected_lang = query['data'][-2:]
    db.set_user_lang(user_id, selected_lang)
    await query.message.delete()
    await query.message.answer(text=lang.get_lang_settings_text("LANG_SETTINGS", "SUCCESS", selected_lang),
                               reply_markup=markup.get_main_menu_markup(selected_lang))
    await query.answer()


def main():
    """Application entry point"""
    # TODO: Change to webhooks in production
    executor.start_polling(dp, skip_updates=True)


if __name__ == '__main__':
    main()
