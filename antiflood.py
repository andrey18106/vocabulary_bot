# -*- coding: utf-8 -*-

# ===== Default imports =====

import asyncio
import logging

# ===== External libs imports =====

from aiogram import Dispatcher, types
from aiogram.dispatcher.handler import CancelHandler, current_handler
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.utils.exceptions import Throttled

# ===== Local imports =====

from lang_manager import LangManager


class VocabularyBotAntifloodMiddleware(BaseMiddleware):

    def __init__(self, lang_manager: LangManager, limit=2, key_prefix='antiflood_'):
        self.lang = lang_manager
        self.rate_limit = limit
        self.prefix = key_prefix
        super(VocabularyBotAntifloodMiddleware, self).__init__()

    @staticmethod
    def rate_limit(limit: int, key=None):
        """
        Decorator for configuring rate limit and key in different functions.

        :param limit:
        :param key:
        :return:
        """
        def decorator(func):
            setattr(func, 'throttling_rate_limit', limit)
            if key:
                setattr(func, 'throttling_key', key)
            return func
        return decorator

    async def on_process_message(self, message: types.Message, data: dict):
        """
        This handler is called when dispatcher receives a message

        :param message:
        """
        # Get current handler
        handler = current_handler.get()

        # Get dispatcher from context
        dispatcher = Dispatcher.get_current()
        # If handler was configured, get rate limit and key from handler
        if handler:
            limit = getattr(handler, 'throttling_rate_limit', self.rate_limit)
            key = getattr(handler, 'throttling_key', f"{self.prefix}_{handler.__name__}")
        else:
            limit = self.rate_limit
            key = f"{self.prefix}_message"

        # Use Dispatcher.throttle method.
        try:
            await dispatcher.throttle(key, rate=limit)
        except Throttled as t:
            # Log the throttling issue
            logging.getLogger(type(self).__name__).error(t)

            # Execute action
            await self.message_throttled(message, t)

            # Cancel current handler
            raise CancelHandler()

    async def message_throttled(self, message: types.Message, throttled: Throttled):
        """
        Notify user only on first exceed and notify about unlocking only on last exceed

        :param message:
        :param throttled:
        """
        handler = current_handler.get()
        dispatcher = Dispatcher.get_current()
        if handler:
            key = getattr(handler, 'throttling_key', f"{self.prefix}_{handler.__name__}")
        else:
            key = f"{self.prefix}_message"

        # Calculate how many time is left till the block ends
        delta = throttled.rate - throttled.delta

        # Prevent flooding
        if throttled.exceeded_count <= 2:
            user_lang = self.lang.parse_user_lang(message['from']['id'])
            await message.reply(self.lang.get_page_text('THROTTLING', 'TOO_MANY_REQUESTS', user_lang))

        # Sleep.
        await asyncio.sleep(delta)

        # Check lock status
        thr = await dispatcher.check_key(key)

        # If current message is not last with current key - do not send message
        if thr.exceeded_count == throttled.exceeded_count:
            await message.reply('Unlocked.')
