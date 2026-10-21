from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config.settings import settings


session = AiohttpSession(
    proxy="http://127.0.0.1:10808"
)


from middlewares.premium_emoji import PremiumEmojiMiddleware
from middlewares.premium_emoji_buttons import PremiumEmojiButtonsMiddleware
from middlewares.auto_delete_previous import AutoDeletePreviousMessageMiddleware

session.middleware(PremiumEmojiButtonsMiddleware())
session.middleware(PremiumEmojiMiddleware())
session.middleware(AutoDeletePreviousMessageMiddleware())

bot = Bot(
    token=settings.bot_token,
    session=session,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML,
    ),
)