from aiogram import Router
from aiogram.types import Message
from sqlalchemy import delete

from config.settings import settings
from database.database import AsyncSessionLocal
from models.character import Character


router = Router()


@router.message(lambda message: message.text == "/myid")
async def my_id_handler(message: Message):

    await message.answer(
        f"🆔 Telegram ID شما:\n\n{message.from_user.id}"
    )


@router.message(
    lambda message: message.text
    and message.text.startswith("/delete_player")
)
async def delete_player_handler(message: Message):

    # بررسی ادمین اصلی
    if message.from_user.id != settings.admin_id:
        await message.answer(
            "⛔ شما دسترسی ادمین ندارید."
        )
        return

    parts = message.text.split()

    if len(parts) != 2:
        await message.answer(
            "❌ فرمت دستور صحیح نیست.\n\n"
            "مثال:\n"
            "/delete_player 8252584456"
        )
        return

    try:
        telegram_id = int(parts[1])
    except ValueError:
        await message.answer(
            "❌ Telegram ID باید عددی باشد."
        )
        return

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            delete(Character).where(
                Character.telegram_id == telegram_id
            )
        )

        await session.commit()

        if result.rowcount == 0:
            await message.answer(
                "⚠️ شخصیتی با این Telegram ID پیدا نشد."
            )
            return

    await message.answer(
        "✅ شخصیت با موفقیت حذف شد.\n\n"
        f"🆔 Telegram ID: {telegram_id}"
    )