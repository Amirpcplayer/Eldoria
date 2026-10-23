from __future__ import annotations

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery

from services.premium_emoji_service import apply_keyboard_icons


OWNER_PREFIX = "eo:"


def protect_keyboard(reply_markup, owner_id: int):
    if reply_markup is None:
        return None

    # Apply configured Telegram custom-emoji icons before owner-protecting
    # callback data, so the emoji resolver sees the original callback names.
    reply_markup = apply_keyboard_icons(reply_markup)

    rows = []

    for row in reply_markup.inline_keyboard:
        protected_row = []

        for button in row:
            callback_data = button.callback_data

            if callback_data is None:
                protected_row.append(button)
                continue

            # دکمه‌ای که قبلاً محافظت شده است.
            if callback_data.startswith(OWNER_PREFIX):
                try:
                    _, owner_text, _ = callback_data.split(":", 2)
                    existing_owner = int(owner_text)
                except (ValueError, TypeError):
                    raise ValueError(
                        f"Invalid protected callback: {callback_data}"
                    )

                # دکمه متعلق به بازیکن دیگری است؛ آن را به مالک جدید
                # نسبت نده.
                if existing_owner != owner_id:
                    raise ValueError(
                        "Cannot reuse another player's protected keyboard."
                    )

                protected_row.append(button)
                continue

            protected_data = f"{OWNER_PREFIX}{owner_id}:{callback_data}"

            if len(protected_data.encode("utf-8")) > 64:
                raise ValueError(
                    f"callback_data exceeds Telegram's 64-byte limit: "
                    f"{callback_data}"
                )

            protected_row.append(
                button.model_copy(
                    update={"callback_data": protected_data}
                )
            )

        rows.append(protected_row)

    return reply_markup.model_copy(
        update={"inline_keyboard": rows}
    )


class PanelOwnerMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)

        callback_data = event.data

        if not callback_data or not callback_data.startswith(OWNER_PREFIX):
            return await handler(event, data)

        try:
            _, owner_text, original_data = callback_data.split(":", 2)
            owner_id = int(owner_text)

        except (ValueError, TypeError):
            await event.answer(
                "⚠️ اطلاعات این دکمه معتبر نیست.",
                show_alert=True,
            )
            return None

        if event.from_user.id != owner_id:
            await event.answer(
                "⛔ این پنل برای شما نیست!",
                show_alert=True,
            )
            return None

        # داده اصلی قبل از اجرای فیلترهای هندلر بازیابی می‌شود.
        original_event = event.model_copy(
            update={"data": original_data}
        )

        return await handler(original_event, data)