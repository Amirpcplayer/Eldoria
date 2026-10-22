from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from config.panel_images import PANEL_IMAGES
from database.redis import redis
from middlewares.panel_owner import protect_keyboard

logger = logging.getLogger(__name__)
PANEL_REFERENCE_TTL = 60 * 60 * 24 * 30


def get_panel_image(panel_name: str) -> Path | None:
    """Return a configured panel image, if one exists on disk."""
    image_path = PANEL_IMAGES.get(panel_name)
    if not image_path:
        return None
    path = Path(image_path)
    return path if path.is_file() else None


def _reference_key(chat_id: int, owner_id: int) -> str:
    return f"eldoria:panel_reference:v2:{chat_id}:{owner_id}"


async def _save_reference(chat_id: int, owner_id: int, message_id: int) -> None:
    try:
        await redis.set(
            _reference_key(chat_id, owner_id),
            str(message_id),
            ex=PANEL_REFERENCE_TTL,
        )
    except Exception:
        # Panel editing should still work if Redis is temporarily unavailable.
        logger.exception("Could not save panel reference")


async def remember_panel_message(message: Message, owner_id: int | None = None) -> None:
    """Remember the actual bot panel message, never the user's command message."""
    resolved_owner = owner_id
    if resolved_owner is None:
        resolved_owner = message.from_user.id if message.from_user else None
    if resolved_owner is not None:
        await _save_reference(message.chat.id, resolved_owner, message.message_id)


def _is_media_message(message: Message) -> bool:
    return bool(
        message.photo
        or message.video
        or message.animation
        or message.document
        or message.audio
        or message.voice
        or message.video_note
        or message.sticker
    )


async def replace_panel_with_text(
    callback: CallbackQuery,
    text: str,
    reply_markup=None,
    parse_mode: ParseMode | str | None = ParseMode.HTML,
    protect_owner: bool = True,
) -> Message | None:
    """Keep a player menu in one bot message; replace media messages when text is needed."""
    message = callback.message
    if message is None:
        return None

    owner_id = callback.from_user.id
    keyboard = protect_keyboard(reply_markup, owner_id) if protect_owner else reply_markup

    if not _is_media_message(message):
        try:
            await message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode=parse_mode,
            )
            await _save_reference(message.chat.id, owner_id, message.message_id)
            return message
        except TelegramBadRequest as exc:
            if "message is not modified" in str(exc).casefold():
                await _save_reference(message.chat.id, owner_id, message.message_id)
                return message
            logger.debug(
                "Panel text edit failed; replacing the bot panel (chat=%s, message=%s): %s",
                message.chat.id,
                message.message_id,
                exc,
            )
        except Exception:
            logger.exception("Unexpected error editing player panel")

    # Telegram cannot turn a photo/caption into a text message. Delete only this
    # bot panel and send its text replacement; never target another user's message.
    try:
        await message.delete()
    except Exception:
        logger.debug("Could not delete old panel before replacement", exc_info=True)

    sent = await message.answer(
        text,
        reply_markup=keyboard,
        parse_mode=parse_mode,
    )
    await _save_reference(sent.chat.id, owner_id, sent.message_id)
    return sent


async def replace_panel_with_photo(
    callback: CallbackQuery,
    photo: Any,
    caption: str,
    reply_markup=None,
    parse_mode: ParseMode | str | None = ParseMode.HTML,
) -> Message | None:
    """Replace the current player panel with an image panel (profile/Fan Art)."""
    message = callback.message
    if message is None:
        return None

    owner_id = callback.from_user.id
    keyboard = protect_keyboard(reply_markup, owner_id)

    try:
        await message.delete()
    except Exception:
        # The following send is still useful if Telegram no longer allows deletion.
        logger.debug("Could not delete old panel before photo replacement", exc_info=True)

    sent = await message.answer_photo(
        photo=photo,
        caption=caption,
        reply_markup=keyboard,
        parse_mode=parse_mode,
    )
    await _save_reference(sent.chat.id, owner_id, sent.message_id)
    return sent


async def send_panel(
    message: Message,
    panel_name: str,
    text: str,
    reply_markup=None,
    parse_mode: ParseMode | str | None = ParseMode.HTML,
) -> Message | None:
    """Edit this player's previous panel when available; otherwise send the first one."""
    if message.from_user is None:
        raise ValueError("Cannot determine panel owner.")

    owner_id = message.from_user.id
    chat_id = message.chat.id
    keyboard = protect_keyboard(reply_markup, owner_id)
    image_path = get_panel_image(panel_name)

    # v2 references are written only for bot-owned panel messages. This avoids
    # legacy keys that previously pointed at the user's /menu command.
    previous_id = await _get_reference(chat_id, owner_id)
    if previous_id is not None:
        if image_path is None:
            try:
                edited = await message.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=previous_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode=parse_mode,
                )
                if isinstance(edited, Message):
                    await _save_reference(chat_id, owner_id, edited.message_id)
                return edited if isinstance(edited, Message) else None
            except TelegramBadRequest as exc:
                if "message is not modified" in str(exc).casefold():
                    return None
                logger.debug("Could not edit previous panel; replacing it: %s", exc)
            except Exception:
                logger.exception("Unexpected error editing previous panel")

        # The known v2 reference is a bot-owned panel. A media panel must be
        # replaced because Telegram cannot edit its message type into plain text.
        try:
            await message.bot.delete_message(chat_id=chat_id, message_id=previous_id)
        except Exception:
            logger.debug("Could not delete previous panel before command replacement", exc_info=True)

    if image_path is not None:
        from aiogram.types import FSInputFile
        sent = await message.answer_photo(
            photo=FSInputFile(image_path),
            caption=text,
            reply_markup=keyboard,
            parse_mode=parse_mode,
            reply_to_message_id=message.message_id,
            allow_sending_without_reply=True,
        )
    else:
        sent = await message.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode=parse_mode,
            reply_to_message_id=message.message_id,
            allow_sending_without_reply=True,
        )

    await _save_reference(sent.chat.id, owner_id, sent.message_id)
    return sent

async def show_panel(
    callback: CallbackQuery,
    panel_name: str,
    text: str,
    reply_markup=None,
    parse_mode: ParseMode | str | None = ParseMode.HTML,
) -> Message | None:
    """Render every ordinary game panel by editing the current panel message."""
    # Normal game panels are text-only. Image panels are handled explicitly by
    # profile/Fan Art/boss handlers so they can be re-sent when the media changes.
    return await replace_panel_with_text(
        callback=callback,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
    )
