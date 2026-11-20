from __future__ import annotations

import asyncio
import html
import logging
import tempfile
from pathlib import Path
from typing import Awaitable, Callable

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from config.settings import settings
from services.safe_update import UpdateArchiveError, apply_update_archive

router = Router(name="administrator_auto_update")
logger = logging.getLogger(__name__)
_project_root = Path(__file__).resolve().parents[1]
_shutdown_callback: Callable[[], Awaitable[None]] | None = None
_MAX_TELEGRAM_DOCUMENT_BYTES = 20 * 1024 * 1024


class AutoUpdateState(StatesGroup):
    waiting_for_zip = State()


def configure_restart(callback: Callable[[], Awaitable[None]]) -> None:
    """Supply the dispatcher stop callback so the Windows launcher can restart us."""
    global _shutdown_callback
    _shutdown_callback = callback


def _is_owner(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id == settings.admin_id)


@router.message(Command("update"))
async def begin_auto_update(message: Message, state: FSMContext) -> None:
    if not _is_owner(message):
        await message.answer("⛔ این دستور فقط برای مدیر اصلی ربات فعال است.")
        return
    if message.chat.type != "private":
        await message.answer("🔒 برای امنیت، به‌روزرسانی فقط در گفت‌وگوی خصوصی ربات انجام می‌شود.")
        return

    await state.set_state(AutoUpdateState.waiting_for_zip)
    await message.answer(
        "📦 <b>به‌روزرسانی خودکار World Eldoria</b>\n\n"
        "حالا فایل <code>.zip</code> نسخهٔ کامل پروژه را همین‌جا ارسال کن.\n"
        "فایل باید شامل <code>main.py</code>، <code>requirements.txt</code> و پوشهٔ "
        "<code>handlers</code> باشد.\n\n"
        "✅ قبل از جایگزینی، فایل‌های موجود پشتیبان‌گیری می‌شوند.\n"
        "🔒 فایل <code>.env</code>، دیتابیس، محیط <code>.venv</code> و راه‌انداز ویندوز حفظ می‌شوند.\n"
        "⚠️ فقط ZIPای را بفرست که خودت به آن اعتماد داری؛ کدِ بسته بعد از راه‌اندازی اجرا می‌شود.\n\n"
        "برای لغو، /cancel را بفرست."
    )


@router.message(Command("cancel"), StateFilter(AutoUpdateState.waiting_for_zip))
async def cancel_auto_update(message: Message, state: FSMContext) -> None:
    if not _is_owner(message):
        return
    await state.clear()
    await message.answer("عملیات به‌روزرسانی لغو شد.")


@router.message(StateFilter(AutoUpdateState.waiting_for_zip), F.document)
async def receive_update_archive(message: Message, state: FSMContext) -> None:
    if not _is_owner(message) or message.chat.type != "private":
        await state.clear()
        await message.answer("⛔ بارگذاری به‌روزرسانی فقط برای مدیر اصلی و در پی‌وی مجاز است.")
        return

    document = message.document
    if document is None:
        return
    filename = (document.file_name or "").strip()
    if not filename.lower().endswith(".zip"):
        await message.answer("❌ فقط فایل ZIP نسخهٔ کامل پروژه پذیرفته می‌شود. هنوز منتظر ZIP هستم.")
        return
    if document.file_size is not None and document.file_size > _MAX_TELEGRAM_DOCUMENT_BYTES:
        await message.answer("❌ حجم ZIP بیشتر از حد دانلود معمول ربات تلگرام است (۲۰ مگابایت).")
        return

    status = await message.answer("⏳ فایل دریافت شد؛ در حال بررسی ساختار، تهیهٔ نسخهٔ پشتیبان و اعمال به‌روزرسانی...")
    try:
        with tempfile.TemporaryDirectory(prefix="eldoria_telegram_update_") as temp_dir:
            archive_path = Path(temp_dir) / "incoming.zip"
            await message.bot.download(document.file_id, destination=archive_path)
            if archive_path.stat().st_size > _MAX_TELEGRAM_DOCUMENT_BYTES:
                raise UpdateArchiveError("حجم فایل دانلودشده بیشتر از ۲۰ مگابایت است.")
            changed, backup_directory = apply_update_archive(archive_path, _project_root)

        if not changed:
            await state.clear()
            await status.edit_text("✅ فایل معتبر است و تمام فایل‌های قابل‌به‌روزرسانی از قبل یکسان‌اند؛ نیازی به راه‌اندازی مجدد نیست.")
            return

        await state.clear()
        changed_preview = "\n".join(f"• <code>{html.escape(name)}</code>" for name in changed[:20])
        if len(changed) > 20:
            changed_preview += f"\n• و {len(changed) - 20} فایل دیگر"
        await status.edit_text(
            "✅ <b>به‌روزرسانی فایل‌ها اعمال شد.</b>\n\n"
            f"تعداد فایل‌های تغییرکرده: <b>{len(changed)}</b>\n"
            f"{changed_preview}\n\n"
            f"📁 نسخهٔ پشتیبان: <code>{html.escape(backup_directory or '')}</code>\n\n"
            "♻️ ربات اکنون متوقف و توسط <code>run_game.bat</code> دوباره اجرا می‌شود. "
            "این فرایند ممکن است چند لحظه طول بکشد."
        )
        asyncio.create_task(_restart_after_reply(), name="eldoria-auto-restart")
    except UpdateArchiveError as exc:
        await status.edit_text(f"❌ به‌روزرسانی رد شد:\n{exc}\n\nفایل ZIP اصلاح‌شده را ارسال کن یا /cancel بزن.")
    except Exception as exc:
        logger.exception("Administrator uploaded update failed")
        await status.edit_text(
            "❌ هنگام اعمال به‌روزرسانی خطایی رخ داد. نسخهٔ پشتیبان، در صورت ساخته‌شدن، حفظ شده است.\n"
            f"<code>{html.escape(type(exc).__name__ + ': ' + str(exc)[:500])}</code>"
        )


async def _restart_after_reply() -> None:
    # Let Telegram deliver the success message before stopping the polling loop.
    await asyncio.sleep(1.5)
    if _shutdown_callback is None:
        logger.error("Auto-update applied but no dispatcher shutdown callback was configured.")
        return
    await _shutdown_callback()
