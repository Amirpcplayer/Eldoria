from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config.settings import settings


session = AiohttpSession(
    proxy="http://127.0.0.1:10808"
)


from middlewares.auto_delete_previous import AutoDeletePreviousMessageMiddleware
from middlewares.emoji_button_icons import EmojiButtonIconsMiddleware

session.middleware(AutoDeletePreviousMessageMiddleware())
session.middleware(EmojiButtonIconsMiddleware())

bot = Bot(
    token=settings.bot_token,
    session=session,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML,
    ),
)