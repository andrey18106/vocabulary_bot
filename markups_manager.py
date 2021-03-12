# -*- coding: utf-8 -*-

# ===== External libs imports =====

from aiogram import types

# ===== Local imports =====

from lang_manager import LangManager


class MarkupManager:
    """Class for working with Telegram Bot Buttons (markups)"""

    def __init__(self, lang_manager: LangManager):
        self.lang = lang_manager

    def get_main_menu_markup(self, lang_code: str) -> types.ReplyKeyboardMarkup:
        """Returns markup for Main menu"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup_texts = self.lang.get_markup_localization('MAIN_MENU', lang_code)
        if markup_texts is not None:
            markup.add(types.reply_keyboard.KeyboardButton(text=markup_texts[0]))
            markup.add(types.reply_keyboard.KeyboardButton(text=markup_texts[1]))
            for i in range(2, len(markup_texts) - 1, 2):
                markup.add(types.reply_keyboard.KeyboardButton(text=markup_texts[i]),
                           types.reply_keyboard.KeyboardButton(text=markup_texts[i + 1]))
        return markup

    def get_settings_markup(self, lang_code: str) -> types.InlineKeyboardMarkup:
        """Returns settings page markup"""
        markup = types.InlineKeyboardMarkup()
        markup_texts = self.lang.get_markup_localization('SETTINGS', lang_code)
        if markup_texts is not None:
            for button in markup_texts:
                markup.add(types.InlineKeyboardButton(text=button['TEXT'], callback_data=button['CALLBACK_DATA']))
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
                if i < len(markup_texts) - 1:
                    markup.add(types.reply_keyboard.KeyboardButton(text=markup_texts[i]),
                               types.reply_keyboard.KeyboardButton(text=markup_texts[i + 1]))
                else:
                    markup.add(types.reply_keyboard.KeyboardButton(text=markup_texts[i]))
            markup.add(types.reply_keyboard.KeyboardButton(
                text=self.lang.get_page_text('BACK_MAIN_MENU', 'BUTTON', lang_code)))
        return markup

    def get_admin_markup(self, permissions: list, lang_code: str) -> types.ReplyKeyboardMarkup:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup_texts = self.lang.get_markup_localization('ADMIN', lang_code)
        if markup_texts is not None:
            for i in range(0, len(markup_texts) - 1, 2):
                markup.add(types.reply_keyboard.KeyboardButton(text=markup_texts[i]),
                           types.reply_keyboard.KeyboardButton(text=markup_texts[i + 1]))
        markup.add(
            types.reply_keyboard.KeyboardButton(text=self.lang.get_page_text("BACK_MAIN_MENU", "BUTTON", lang_code)))
        return markup

    def get_dict_pagination(self, action: str) -> types.InlineKeyboardMarkup:
        """TODO: Implement dict pagination"""
        pagination_markup = types.InlineKeyboardMarkup()
        pagination_markup.row(types.InlineKeyboardButton(text="⏮", callback_data=f'first_{action}'),
                              types.InlineKeyboardButton(text="⬅", callback_data=f'prev_{action}'),
                              types.InlineKeyboardButton(text="➡", callback_data=f'next_{action}'),
                              types.InlineKeyboardButton(text="⏭", callback_data=f'last_{action}'))
        return pagination_markup

    def get_help_back_markup(self, user_lang: str) -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text=self.lang.get_page_text("HELP", "BACK", user_lang),
                                              callback_data=self.lang.get_page_text("HELP", "BACK_CALLBACK",
                                                                                    user_lang)))
        return markup

    def get_admin_database_markup(self, lang_code: str) -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup()
        return markup

    def get_profile_referral_markup(self, lang_code: str) -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(text=self.lang.get_page_text("PROFILE", "REFERRAL_BUTTON_TEXT", lang_code),
                                       callback_data="profile_referral_link"))
        return markup

    def get_confirmation_markup(self, lang_code: str) -> types.ReplyKeyboardMarkup:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup_texts = self.lang.get_markup_localization('ADD_WORD', lang_code)
        if markup_texts is not None:
            for text in markup_texts:
                markup.add(types.reply_keyboard.KeyboardButton(text))
        return markup

    def get_cancel_markup(self) -> types.ReplyKeyboardMarkup:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.reply_keyboard.KeyboardButton(text='/cancel'))
        return markup

    def get_mailings_markup(self, user_lang) -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup()
        markup_texts = self.lang.get_markup_localization('MAILINGS', user_lang)
        if markup_texts is not None:
            for button in markup_texts:
                markup.add(types.InlineKeyboardButton(text=button['TEXT'], callback_data=button['CALLBACK_DATA']))
        return markup
