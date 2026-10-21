from __future__ import annotations

from pathlib import Path

from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, FSInputFile, Message

from config.panel_images import PANEL_IMAGES
from database.redis import redis
from middlewares.panel_owner import protect_keyboard


PANEL_REFERENCE_TTL = 60 * 60 * 24 * 30


def get_panel_image(panel_name: str) -> Path | None:
    image_path = PANEL_IMAGES.get(panel_name)

    if not image_path:
        return None

    path = Path(image_path)

    if not path.is_file():
        return None

    return path


def _reference_key(chat_id: int, owner_id: int) -> str:
    return f"eldoria:panel_reference:{chat_id}:{owner_id}"


async def _save_reference(
    chat_id: int,
    owner_id: int,
    message_id: int,
) -> None:
    # Redis is only used to remember which message should be replaced.
    # A Redis outage must not make every menu button fail.
    try:
        await redis.set(
            _reference_key(chat_id, owner_id),
            str(message_id),
            ex=PANEL_REFERENCE_TTL,
        )
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "Could not save panel reference; continuing without Redis"
        )


async def _get_reference(
    chat_id: int,
    owner_id: int,
) -> int | None:
    try:
        value = await redis.get(_reference_key(chat_id, owner_id))
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "Could not read panel reference; using current message"
        )
        return None

    if not value:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


async def send_panel(
    message: Message,
    panel_name: str,
    text: str,
    reply_markup=None,
    parse_mode: ParseMode | str | None = ParseMode.HTML,
):
    """ارسال پنل در پاسخ به پیام بازیکن و ذخیره مرجع آن."""

    if message.from_user is None:
        raise ValueError("Cannot determine panel owner.")

    owner_id = message.from_user.id
    chat_id = message.chat.id

    # در شروع بازی، خود پیام /start مرجع اصلی پنل است.
    reference_message_id = message.message_id

    await _save_reference(
        chat_id,
        owner_id,
        reference_message_id,
    )

    keyboard = protect_keyboard(reply_markup, owner_id)
    image_path = get_panel_image(panel_name)

    if image_path is not None:
        return await message.answer_photo(
            photo=FSInputFile(image_path),
            caption=text,
            reply_markup=keyboard,
            parse_mode=parse_mode,
            reply_to_message_id=reference_message_id,
            allow_sending_without_reply=True,
        )

    return await message.answer(
        text=text,
        reply_markup=keyboard,
        parse_mode=parse_mode,
        reply_to_message_id=reference_message_id,
        allow_sending_without_reply=True,
    )


async def show_panel(
    callback: CallbackQuery,
    panel_name: str,
    text: str,
    reply_markup=None,
    parse_mode: ParseMode | str | None = ParseMode.HTML,
):
    """Send a fresh panel message without deleting or editing earlier messages.

    The only intentionally live-updated UI in the game is the group-boss
    battle message; ordinary menu navigation keeps the chat history intact.
    """
    message = callback.message
    if message is None:
        await callback.answer()
        return None

    owner_id = callback.from_user.id
    chat_id = message.chat.id
    reference_message_id = await _get_reference(chat_id, owner_id)
    if reference_message_id is None:
        # Save the first known message as the reply anchor, but never remove it.
        reference_message_id = message.message_id
        await _save_reference(chat_id, owner_id, reference_message_id)

    keyboard = protect_keyboard(reply_markup, owner_id)
    image_path = get_panel_image(panel_name)
    send_kwargs = {
        "reply_to_message_id": reference_message_id,
        "allow_sending_without_reply": True,
    }

    if image_path is not None:
        return await message.answer_photo(
            photo=FSInputFile(image_path),
            caption=text,
            reply_markup=keyboard,
            parse_mode=parse_mode,
            **send_kwargs,
        )

    return await message.answer(
        text=text,
        reply_markup=keyboard,
        parse_mode=parse_mode,
        **send_kwargs,
    )
