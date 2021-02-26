# -*- coding: utf-8 -*-

# ===== Default imports =====

import logging
import functools

# ===== External libs imports =====

from aiogram import types

# ===== Local imports =====

from db_manager import DbManager


class BotAnalytics:
    """Class for collecting bot usage analytics and other metrics"""

    def __init__(self, db_manager: DbManager):
        self.db = db_manager

    def default_metric(self, message_handler):
        """Decorator for message handlers. Collects message data (user, handler) and stores in DB"""
        @functools.wraps(message_handler)
        def decorator(message: types.Message):
            self._log_message_handler(message_handler.__name__, message['from']['id'])
            return message_handler(message)
        return decorator

    def _log_message_handler(self, handler_name: str, user_id: int) -> None:
        self.db.log_default_metric(handler_name, user_id, self.db.get_metric_id(handler_name))
        logging.getLogger(type(self).__name__).info(f'[{user_id}] Analytics message handler executed [{handler_name}]')

    def callback_metric(self, callback_handler):
        """Decorator for callback handlers. Collects data (user, handler) and stores in DB"""
        @functools.wraps(callback_handler)
        def decorator(query: types.CallbackQuery):
            self._log_callback_handler(callback_handler.__name__, query['from']['id'])
            return callback_handler(query)
        return decorator

    def _log_callback_handler(self, callback_name: str, user_id: int) -> None:
        self.db.log_callback_metric(callback_name, user_id, self.db.get_metric_id(callback_name))
        logging.getLogger(type(self).__name__).info(
            f'[{user_id}] Analytics callback handler executed [{callback_name}]')
