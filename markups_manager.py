# -*- coding: utf-8 -*-

# ===== External libs imports =====

from aiogram import types

# ===== Local imports =====

from lang_manager import LangManager


# TODO: Export menus and buttons hierarchy to appropriate file


class MarkupManager:
    """Class for working with Telegram Bot Buttons (markups)"""

    def __init__(self, lang_manager: LangManager):
        self.lang = lang_manager

    def get_main_menu_markup(self, lang_code: str) -> types.ReplyKeyboardMarkup:
        """Returns markup for Main menu"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup_texts = self.lang.get_markup_localization('MAIN_MENU', lang_code)
        if markup_texts is not None:
            for i in range(0, len(markup_texts) - 2):
                markup.add(types.reply_keyboard.KeyboardButton(text=markup_texts[i]))
            markup.add(types.reply_keyboard.KeyboardButton(text=markup_texts[(len(markup_texts) - 2)]),
                       types.reply_keyboard.KeyboardButton(text=markup_texts[(len(markup_texts) - 1)]))
        return markup

    def get_lang_settings_markup(self, lang_code: str) -> types.InlineKeyboardMarkup:
        """Returns inline markup for Language Settings page"""
        markup = types.InlineKeyboardMarkup()
        markup_texts = self.lang.get_inline_markup_localization('LANG_SETTINGS', lang_code)
        if markup_texts is not None:
            for button in markup_texts:
                markup.add(types.InlineKeyboardButton(text=button['TEXT'], callback_data=button['CALLBACK_DATA']))
        return markup

    def get_help_markup(self, lang_code: str) -> types.InlineKeyboardMarkup:
        """Returns inline markup for Help page"""
        markup = types.InlineKeyboardMarkup()
        markup_texts = self.lang.get_inline_markup_localization('HELP', lang_code)
        if markup_texts is not None:
            for button in markup_texts:
                markup.add(types.InlineKeyboardButton(text=button['TEXT'], callback_data=button['CALLBACK_DATA']))
        return markup

    def get_dictionary_markup(self, lang_code: str) -> types.ReplyKeyboardMarkup:
        """Returns inline markup for Dictionary page"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup_texts = self.lang.get_inline_markup_localization('DICTIONARY', lang_code)
        if markup_texts is not None:
            for i in range(0, len(markup_texts), 2):
                if i < len(markup_texts) - 2:
                    markup.add(types.reply_keyboard.KeyboardButton(text=markup_texts[i]),
                               types.reply_keyboard.KeyboardButton(text=markup_texts[i + 1]))
                else:
                    markup.add(types.reply_keyboard.KeyboardButton(text=markup_texts[i]))
            markup.add(types.reply_keyboard.KeyboardButton(
                text=self.lang.get_page_text('BACK_MAIN_MENU', 'BUTTON', lang_code)))
        return markup

    def get_admin_markup(self, permissions: list, lang_code: str) -> types.ReplyKeyboardMarkup:
        """TODO: Admin markup"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup_texts = self.lang.get_markup_localization('ADMIN', lang_code)
        if markup_texts is not None:
            for button_text in markup_texts:
                markup.add(types.reply_keyboard.KeyboardButton(text=button_text))
        markup.add(
            types.reply_keyboard.KeyboardButton(text=self.lang.get_page_text("BACK_MAIN_MENU", "BUTTON", lang_code)))
        return markup

    def get_dict_pagination(self, user_id: int, lang_code: str) -> types.InlineKeyboardMarkup:
        """TODO: Implement dict pagination"""
        pass
