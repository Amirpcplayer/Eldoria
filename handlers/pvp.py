from __future__ import annotations

import asyncio
import html
import logging
import secrets
import time

from aiogram import F, Router
from aiogram.filters import BaseFilter, Command
from aiogram.types import CallbackQuery, Message

from bot.bot import bot
from database.redis import redis
from keyboards.pvp import (
    pvp_battle_keyboard,
    pvp_potions_keyboard,
    pvp_request_keyboard,
    pvp_skills_keyboard,
)
from services.direct_pvp_service import direct_attack, direct_pet_attack, PET_ATTACKS_PER_WINDOW, PET_ATTACK_WINDOW
from database.database import AsyncSessionLocal
from models.character import Character
from models.world_systems import PvpBounty
from models.social_systems import CharacterPet, Pet
from sqlalchemy import select
from datetime import datetime
import re
from services.pvp_service import (
    PVP_TURN_SECONDS,
    create_pvp_battle,
    expire_pvp_turn,
    get_player_skills,
    get_pvp_battle,
    get_pvp_healing_potions,
    perform_pvp_action,
    save_pvp_panel_location,
)


router = Router(name="pvp")
logger = logging.getLogger(__name__)

PENDING_REQUESTS: dict[str, dict] = {}
REQUEST_TTL = 300

TURN_TASKS: dict[str, asyncio.Task] = {}

PVP_PREFIX = "eldoria:pvp_battle:"


def _cleanup_requests() -> None:
    now = time.time()

    for request_id in list(PENDING_REQUESTS):
        created_at = PENDING_REQUESTS[request_id].get(
            "created_at",
            0,
        )

        if now - created_at > REQUEST_TTL:
            PENDING_REQUESTS.pop(request_id, None)


async def _get_active_pvp(telegram_id: int) -> dict | None:
    """
    اگر بازیکن عضو یک PvP فعال است، اطلاعات همان مبارزه را برمی‌گرداند.
    کلیدهای قفل Redis به‌عنوان مبارزه در نظر گرفته نمی‌شوند.
    """
    try:
        keys = await redis.keys(f"{PVP_PREFIX}*")

        for key in keys:
            if isinstance(key, bytes):
                key = key.decode("utf-8")

            key = str(key)

            if not key.startswith(PVP_PREFIX):
                continue

            battle_id = key[len(PVP_PREFIX):]

            # کلیدهای قفل، اطلاعات خود مبارزه نیستند.
            if not battle_id or battle_id.endswith(":lock"):
                continue

            battle = await get_pvp_battle(battle_id)

            if battle is None or battle.get("finished"):
                continue

            if telegram_id in (
                int(battle["player1_id"]),
                int(battle["player2_id"]),
            ):
                return battle

    except Exception:
        logger.exception(
            "Failed to check active PvP for player %s",
            telegram_id,
        )
        raise

    return None


async def _player_pvp_error(
    challenger_id: int,
    opponent_id: int,
) -> str | None:
    """
    پیش از ارسال دعوت یا پذیرش آن، وضعیت هر دو بازیکن را بررسی می‌کند.
    """
    challenger_battle = await _get_active_pvp(challenger_id)

    if challenger_battle is not None:
        return "❌ شما در حال حاضر در یک مبارزهٔ PvP هستید؛ ابتدا آن را تمام کنید."

    opponent_battle = await _get_active_pvp(opponent_id)

    if opponent_battle is not None:
        return "❌ بازیکن موردنظر در حال حاضر در یک مبارزهٔ PvP است."

    return None


def _battle_text(
    battle: dict,
    action_text: str | None = None,
) -> str:
    p1_name = html.escape(str(battle["player1_name"]))
    p2_name = html.escape(str(battle["player2_name"]))

    text = (
        "⚔️ <b>مبارزه PvP اِلدوریا</b>\n\n"
        f"🗡️ <b>{p1_name}</b> — Lv.{battle['player1_level']}\n"
        f"❤️ HP: {battle['player1_hp']}/{battle['player1_max_hp']}\n"
        f"🔵 Mana: {battle['player1_mana']}/{battle['player1_max_mana']}\n"
        f"⚔️ ATK: {battle['player1_attack']} | "
        f"✨ Magic: {battle['player1_magic_power']}\n"
        f"🛡️ DEF: {battle['player1_defense']} | "
        f"🔰 MDEF: {battle['player1_magic_defense']}\n"
        f"🧪 درمان: {battle.get('player1_heals_total', 0)}/5\n\n"
        "━━━━━━━━━━━━━━\n\n"
        f"🛡️ <b>{p2_name}</b> — Lv.{battle['player2_level']}\n"
        f"❤️ HP: {battle['player2_hp']}/{battle['player2_max_hp']}\n"
        f"🔵 Mana: {battle['player2_mana']}/{battle['player2_max_mana']}\n"
        f"⚔️ ATK: {battle['player2_attack']} | "
        f"✨ Magic: {battle['player2_magic_power']}\n"
        f"🛡️ DEF: {battle['player2_defense']} | "
        f"🔰 MDEF: {battle['player2_magic_defense']}\n"
        f"🧪 درمان: {battle.get('player2_heals_total', 0)}/5\n"
    )

    if action_text:
        text += f"\n\n{action_text}"

    if battle["finished"]:
        winner_id = battle["winner_id"]

        if winner_id == battle["player1_id"]:
            winner_name = p1_name
        elif winner_id == battle["player2_id"]:
            winner_name = p2_name
        else:
            winner_name = "نامشخص"

        text += f"\n\n🏆 <b>برنده: {winner_name}</b>"

    else:
        if battle["turn"] == battle["player1_id"]:
            turn_name = p1_name
        else:
            turn_name = p2_name

        remaining = max(
            0,
            int(
                float(battle.get("turn_deadline", 0) or 0)
                - time.time()
            ),
        )

        text += (
            f"\n\n🎯 نوبت: <b>{turn_name}</b>"
            f"\n⏳ مهلت این نوبت: <b>{remaining} ثانیه</b>"
            "\n\n🧪 در هر نوبت حداکثر ۲ بار و در کل مبارزه ۵ بار درمان مجاز است."
        )

    return text


async def _edit_battle_message(
    chat_id: int,
    message_id: int,
    battle: dict,
    action_text: str | None = None,
) -> bool:
    markup = (
        None
        if battle["finished"]
        else pvp_battle_keyboard(battle["battle_id"])
    )

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=_battle_text(battle, action_text),
            reply_markup=markup,
            parse_mode="HTML",
        )
        return True

    except Exception as exc:
        if "message is not modified" in str(exc).lower():
            return True

        logger.exception("Failed to update PvP panel")
        return False


async def _edit_battle_panel(
    callback: CallbackQuery,
    battle: dict,
    action_text: str | None = None,
) -> bool:
    if callback.message is None:
        return False

    return await _edit_battle_message(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        battle=battle,
        action_text=action_text,
    )


def _cancel_turn_timer(battle_id: str) -> None:
    task = TURN_TASKS.pop(battle_id, None)

    if task is not None and not task.done():
        if task is not asyncio.current_task():
            task.cancel()


def _schedule_turn_timer(battle: dict) -> None:
    battle_id = str(battle["battle_id"])

    if battle.get("finished"):
        _cancel_turn_timer(battle_id)
        return

    deadline = float(battle.get("turn_deadline", 0) or 0)

    if deadline <= 0:
        _cancel_turn_timer(battle_id)
        return

    current_task = asyncio.current_task()
    old_task = TURN_TASKS.get(battle_id)

    if old_task is current_task:
        TURN_TASKS.pop(battle_id, None)
    elif old_task is not None and not old_task.done():
        old_task.cancel()

    TURN_TASKS[battle_id] = asyncio.create_task(
        _turn_timer(battle_id, deadline)
    )


async def _turn_timer(
    battle_id: str,
    expected_deadline: float,
) -> None:
    current_task = asyncio.current_task()

    try:
        await asyncio.sleep(
            max(0, expected_deadline - time.time())
        )

        result = await expire_pvp_turn(
            battle_id,
            expected_deadline=expected_deadline,
        )

        if result is None:
            return

        battle, action_text = result

        chat_id = battle.get("chat_id")
        message_id = battle.get("message_id")

        if chat_id and message_id:
            await _edit_battle_message(
                chat_id=int(chat_id),
                message_id=int(message_id),
                battle=battle,
                action_text=action_text,
            )

        if TURN_TASKS.get(battle_id) is current_task:
            TURN_TASKS.pop(battle_id, None)

        if not battle.get("finished"):
            _schedule_turn_timer(battle)

    except asyncio.CancelledError:
        raise

    except Exception:
        logger.exception(
            "PvP turn timer failed for battle %s",
            battle_id,
        )

    finally:
        if TURN_TASKS.get(battle_id) is current_task:
            TURN_TASKS.pop(battle_id, None)


async def _validate_turn(
    callback: CallbackQuery,
    battle_id: str,
) -> dict | None:
    battle = await get_pvp_battle(battle_id)

    if battle is None:
        await callback.answer(
            "❌ این مبارزه دیگر فعال نیست.",
            show_alert=True,
        )
        return None

    if battle["finished"]:
        await callback.answer(
            "🏁 این مبارزه تمام شده است.",
            show_alert=True,
        )
        return None

    if callback.from_user.id not in (
        battle["player1_id"],
        battle["player2_id"],
    ):
        await callback.answer(
            "⛔ شما عضو این مبارزه نیستید.",
            show_alert=True,
        )
        return None

    deadline = float(battle.get("turn_deadline", 0) or 0)

    if deadline <= time.time():
        expired = await expire_pvp_turn(
            battle_id,
            expected_deadline=deadline,
        )

        if expired is not None:
            updated, action_text = expired
            await _edit_battle_panel(
                callback,
                updated,
                action_text,
            )
            _schedule_turn_timer(updated)

            await callback.answer(
                "⌛ مهلت تمام شد و نوبت به حریف رسید.",
                show_alert=True,
            )
            return None

        battle = await get_pvp_battle(battle_id)

        if battle is None or battle["finished"]:
            await callback.answer(
                "🏁 این مبارزه تمام شده است.",
                show_alert=True,
            )
            return None

        if float(battle.get("turn_deadline", 0) or 0) <= time.time():
            await callback.answer(
                "⌛ در حال به‌روزرسانی نوبت؛ دوباره تلاش کن.",
                show_alert=True,
            )
            return None

    if battle["turn"] != callback.from_user.id:
        await callback.answer(
            "⌛ هنوز نوبت شما نیست.",
            show_alert=True,
        )
        return None

    return battle


@router.message(F.text.regexp(r"(?i)^\s*حمله\s*$"))
async def direct_attack_reply_handler(message: Message) -> None:
    """Execute an immediate PvP attack when the player replies with 'حمله'."""
    if message.chat.type not in {"group", "supergroup"}:
        await message.reply("⚔️ برای حمله، در گروه روی پیام بازیکن ریپلای کن و بنویس: حمله")
        return
    if message.from_user is None or message.from_user.is_bot:
        return
    replied = message.reply_to_message
    if replied is None or replied.from_user is None:
        await message.reply("🎯 برای حمله باید روی پیام بازیکن موردنظر ریپلای کنی و بنویسی «حمله».")
        return
    # A Telegram command is not a PvP target, even when a real user sent it.
    # This prevents replies to /menu, /profile, etc. from triggering combat.
    replied_text = (replied.text or replied.caption or "").strip()
    if re.match(r"^/[A-Za-z0-9_]+(?:@[A-Za-z0-9_]+)?(?:\s|$)", replied_text):
        await message.reply("🚫 پیام دستوری هدف PvP نیست. روی پیام عادیِ بازیکن ریپلای کن.")
        return
    target = replied.from_user
    if target.is_bot:
        # پیام باس نیز از طرف حساب ربات ارسال می‌شود؛ ابتدا بررسی کن
        # آیا ریپلای دقیقاً روی پیام یک باس فعال در همین گروه است.
        # فقط در این حالت حمله را به سیستم باس واگذار کن؛ سایر ربات‌ها
        # همچنان هدف معتبر PvP نیستند.
        try:
            from handlers.group_boss import _get_replied_boss, _attack

            replied_boss = await _get_replied_boss(message)
            if replied_boss is not None:
                await _attack(message, boss_id=replied_boss.id)
                return
        except Exception:
            logger.exception("Could not route reply attack to group boss")
            await message.reply("❌ هنگام بررسی پیام باس خطایی رخ داد؛ جزئیات در گزارش ربات ثبت شد.")
            return

        await message.reply("🤖 نمی‌توانی به حساب ربات حمله کنی.")
        return
    if target.id == message.from_user.id:
        await message.reply("🛡️ قهرمان نمی‌تواند به خودش حمله کند.")
        return
    try:
        result = await direct_attack(message.from_user.id, target.id)
    except Exception:
        logger.exception("Direct PvP attack failed")
        await message.reply("❌ اجرای حمله با خطا روبه‌رو شد؛ جزئیات در گزارش ربات ثبت شد.")
        return
    if not result.get("ok"):
        await message.reply(str(result.get("message", "❌ حمله انجام نشد.")))
        return
    attacker_name = html.escape(str(result["attacker_name"]))
    target_name = html.escape(str(result["target_name"]))
    weapon_name = html.escape(str(result["weapon_name"]))
    critical_line = "\n💥 <b>ضربهٔ بحرانی!</b>" if result["critical"] else ""
    pet_ability_line = ""
    if result.get("attacker_pet_ability"):
        pet_ability_line += f"\n🐾 توانایی پت مهاجم: {html.escape(str(result['attacker_pet_ability']))}"
    if result.get("target_pet_ability"):
        pet_ability_line += f"\n🛡️ توانایی پت هدف: {html.escape(str(result['target_pet_ability']))}"
    text = (
        "༺ ⚔️ <b>فرمان خون و فولاد</b> ⚔️ ༻\n\n"
        f"✦ مهاجم: <b>{attacker_name}</b>\n"
        f"✦ حریف: <b>{target_name}</b>\n\n"
        f"تیغهٔ «{weapon_name}» فرود آمد؛ سرنوشت این رویارویی رقم خورد!{critical_line}\n"
        "━━━━━ ✧ ✦ ✧ ━━━━━\n\n"
        f"💥 قدرت ضربه: <b>{int(result['damage']):,}</b>\n"
        f"⚔️ توان مهاجم: ATK {int(result.get('attacker_stats', {}).get('attack', 0))} · CRIT {max(0, min(50, int(result.get('attacker_stats', {}).get('critical', 0))))}%\n"
        f"🛡️ دفاع حریف: DEF {int(result.get('target_stats', {}).get('defense', 0))} · MDEF {int(result.get('target_stats', {}).get('magic_defense', 0))}\n"
        f"❤️ جان باقی‌ماندهٔ {target_name}: <b>{int(result['target_hp']):,} / {int(result['target_max_hp']):,}</b>\n"
        f"🪙 جایزهٔ حمله: <b>+{int(result.get('attack_reward', 0)):,} طلا</b>"
        f"{pet_ability_line}"
    )
    if result["killed"]:
        text += (
            f"\n\n☠️ <b>{target_name} در میدان نبرد سقوط کرد!</b>"
            f"\n🎁 غنیمت منتقل‌شده: <b>+{int(result['loot']):,} طلا</b>"
            "\n✦ قهرمان شکست‌خورده پس از ۱۰ دقیقه با نیروی کامل بازخواهد گشت."
        )
    if int(result.get("bounty_reward", 0)) > 0:
        text += f"\n🏹 جایزهٔ شکار: <b>+{int(result['bounty_reward']):,} طلا</b>"
    await message.reply(text, parse_mode="HTML")


@router.message(Command("pvp"))
async def pvp_command(message: Message) -> None:
    """Compatibility command: /pvp on a reply now attacks immediately, no invitation."""
    if message.chat.type not in {"group", "supergroup"} or message.from_user is None:
        await message.reply("⚔️ برای حمله، در گروه روی پیام بازیکن ریپلای کن و بنویس «حمله».")
        return
    replied = message.reply_to_message
    if replied is None or replied.from_user is None:
        await message.reply("🎯 روی پیام بازیکن ریپلای کن و بنویس «حمله».")
        return
    target = replied.from_user
    if target.is_bot or target.id == message.from_user.id:
        await message.reply("🛡️ این هدف برای حمله معتبر نیست.")
        return
    try:
        result = await direct_attack(message.from_user.id, target.id)
    except Exception:
        logger.exception("Direct PvP /pvp command failed")
        await message.reply("❌ اجرای حمله ناموفق بود.")
        return
    if not result.get("ok"):
        await message.reply(str(result.get("message", "❌ حمله انجام نشد.")))
        return
    attacker_name = html.escape(str(result["attacker_name"]))
    target_name = html.escape(str(result["target_name"]))
    weapon_name = html.escape(str(result["weapon_name"]))
    text = (f"🎯 <b>{attacker_name}</b> <i>({html.escape(str(result.get('attacker_title') or 'شاگرد اِلدوریا'))})</i> ➜ "
            f"<b>{target_name}</b> <i>({html.escape(str(result.get('target_title') or 'شاگرد اِلدوریا'))})</i>\n\n"
            f"⚔️ با «{weapon_name}» ضربه زد و <b>{int(result['damage']):,} آسیب</b> وارد کرد!\n"
            f"📊 ATK مهاجم: {int(result.get('attacker_stats', {}).get('attack', 0))} · DEF هدف: {int(result.get('target_stats', {}).get('defense', 0))}\n"
            f"❤️ HP هدف: <b>{int(result['target_hp']):,}/{int(result['target_max_hp']):,}</b>\n"
            f"💰 پاداش ضربه بر اساس آسیب: <b>+{int(result['attack_reward']):,} طلا</b>")
    if result["killed"]:
        text += f"\n☠️ هدف شکست خورد؛ غارت ۵٪: <b>+{int(result['loot']):,} طلا</b>.\n⏳ احیا پس از ۱۰ دقیقه با HP و مانای کامل."
    await message.reply(text, parse_mode="HTML")


@router.callback_query(F.data.startswith("pvp:accept:"))
async def accept_pvp_request(callback: CallbackQuery) -> None:
    request_id = callback.data.rsplit(":", 1)[-1]
    request = PENDING_REQUESTS.get(request_id)

    if request is None:
        await callback.answer(
            "این درخواست وجود ندارد یا منقضی شده است.",
            show_alert=True,
        )
        return

    if time.time() - request["created_at"] > REQUEST_TTL:
        PENDING_REQUESTS.pop(request_id, None)

        await callback.answer(
            "⏳ مهلت درخواست تمام شده است.",
            show_alert=True,
        )

        if callback.message:
            await callback.message.edit_text(
                "⌛ درخواست PvP منقضی شد."
            )
        return

    if callback.from_user.id != request["opponent_id"]:
        await callback.answer(
            "⛔ این دعوت برای شما ارسال نشده است.",
            show_alert=True,
        )
        return

    # ممکن است بعد از ارسال درخواست، یکی از دو بازیکن وارد PvP دیگری شده باشد.
    try:
        active_error = await _player_pvp_error(
            request["challenger_id"],
            request["opponent_id"],
        )
    except Exception:
        await callback.answer(
            "❌ بررسی وضعیت مبارزه ناموفق بود؛ دوباره تلاش کن.",
            show_alert=True,
        )
        return

    if active_error:
        PENDING_REQUESTS.pop(request_id, None)

        await callback.answer(
            active_error,
            show_alert=True,
        )

        if callback.message:
            try:
                await callback.message.edit_text(
                    active_error
                )
            except Exception:
                logger.exception(
                    "Failed to update rejected PvP request"
                )
        return

    # سرویس اصلی هم وضعیت فعال بودن مبارزه را بررسی می‌کند.
    success, result_message, battle = await create_pvp_battle(
        request["challenger_id"],
        request["opponent_id"],
    )

    if not success or battle is None:
        PENDING_REQUESTS.pop(request_id, None)

        await callback.answer(
            result_message,
            show_alert=True,
        )

        if callback.message:
            try:
                await callback.message.edit_text(
                    "❌ شروع مبارزه ممکن نشد.\n\n"
                    f"{html.escape(result_message)}",
                    parse_mode="HTML",
                )
            except Exception:
                logger.exception(
                    "Failed to display PvP creation error"
                )
        return

    PENDING_REQUESTS.pop(request_id, None)

    if callback.message is None:
        await callback.answer(
            "مبارزه ساخته شد، اما پیام پنل در دسترس نیست.",
            show_alert=True,
        )
        return

    battle = await save_pvp_panel_location(
        battle["battle_id"],
        callback.message.chat.id,
        callback.message.message_id,
    ) or battle

    try:
        await callback.message.edit_text(
            _battle_text(
                battle,
                "⚔️ دعوت پذیرفته شد؛ مبارزه آغاز می‌شود!",
            ),
            reply_markup=pvp_battle_keyboard(battle["battle_id"]),
            parse_mode="HTML",
        )

        _schedule_turn_timer(battle)
        await callback.answer("⚔️ مبارزه آغاز شد!")

    except Exception:
        logger.exception("Failed to display PvP battle")
        await callback.answer(
            "مبارزه ساخته شد، اما نمایش پنل ناموفق بود.",
            show_alert=True,
        )


@router.callback_query(F.data.startswith("pvp:decline:"))
async def decline_pvp_request(callback: CallbackQuery) -> None:
    request_id = callback.data.rsplit(":", 1)[-1]
    request = PENDING_REQUESTS.get(request_id)

    if request is None:
        await callback.answer(
            "این درخواست وجود ندارد یا قبلاً پاسخ داده شده است.",
            show_alert=True,
        )
        return

    if time.time() - request["created_at"] > REQUEST_TTL:
        PENDING_REQUESTS.pop(request_id, None)
        await callback.answer(
            "⏳ مهلت درخواست تمام شده است.",
            show_alert=True,
        )
        return

    if callback.from_user.id != request["opponent_id"]:
        await callback.answer(
            "⛔ فقط بازیکن دعوت‌شده می‌تواند درخواست را رد کند.",
            show_alert=True,
        )
        return

    PENDING_REQUESTS.pop(request_id, None)
    await callback.answer("درخواست رد شد.")

    if callback.message:
        await callback.message.edit_text(
            "❌ درخواست مبارزه رد شد.\n\n"
            f"🗡️ دعوت‌کننده: {html.escape(request['challenger_name'])}\n"
            f"🛡️ بازیکن دعوت‌شده: {html.escape(request['opponent_name'])}",
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("pvp:action:"))
async def pvp_action_handler(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")

    if len(parts) != 4:
        await callback.answer(
            "درخواست نامعتبر است.",
            show_alert=True,
        )
        return

    _, _, battle_id, action = parts

    battle = await _validate_turn(callback, battle_id)

    if battle is None:
        return

    result = await perform_pvp_action(
        battle_id=battle_id,
        telegram_id=callback.from_user.id,
        action=action,
    )

    if not result["ok"]:
        if result.get("timeout"):
            fresh = await get_pvp_battle(battle_id)

            if fresh:
                await _edit_battle_panel(callback, fresh)
                _schedule_turn_timer(fresh)

        await callback.answer(
            result["message"],
            show_alert=True,
        )
        return

    updated = result["battle"]

    displayed = await _edit_battle_panel(
        callback,
        updated,
        result["action_text"],
    )

    if not updated["finished"]:
        _schedule_turn_timer(updated)
    else:
        _cancel_turn_timer(battle_id)

    await callback.answer(
        "🏁 مبارزه تمام شد."
        if result["finished"]
        else "حرکت ثبت شد.",
        show_alert=not displayed,
    )


@router.callback_query(F.data.startswith("pvp:skills:"))
async def pvp_skills_handler(callback: CallbackQuery) -> None:
    battle_id = callback.data.rsplit(":", 1)[-1]
    battle = await _validate_turn(callback, battle_id)

    if battle is None:
        return

    skills = await get_player_skills(
        battle_id,
        callback.from_user.id,
    )

    if not skills:
        await callback.answer(
            "هیچ مهارت فعالی نداری.",
            show_alert=True,
        )
        return

    if callback.message is None:
        await callback.answer()
        return

    own = (
        "player1"
        if callback.from_user.id == battle["player1_id"]
        else "player2"
    )

    try:
        await callback.message.edit_text(
            "🔮 <b>مهارت‌های PvP</b>\n\n"
            f"🔵 مانای فعلی: {battle[f'{own}_mana']}\n\n"
            "مهارت موردنظر را انتخاب کن:",
            reply_markup=pvp_skills_keyboard(battle_id, skills),
            parse_mode="HTML",
        )
        await callback.answer()

    except Exception:
        logger.exception("Failed to show PvP skills")
        await callback.answer(
            "نمایش مهارت‌ها ناموفق بود.",
            show_alert=True,
        )


@router.callback_query(F.data.startswith("pvp:skill:"))
async def pvp_skill_handler(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")

    if len(parts) != 4:
        await callback.answer(
            "درخواست مهارت نامعتبر است.",
            show_alert=True,
        )
        return

    _, _, battle_id, skill_text = parts

    try:
        skill_id = int(skill_text)
    except (TypeError, ValueError):
        await callback.answer(
            "شناسه مهارت نامعتبر است.",
            show_alert=True,
        )
        return

    battle = await _validate_turn(callback, battle_id)

    if battle is None:
        return

    try:
        result = await perform_pvp_action(
            battle_id=battle_id,
            telegram_id=callback.from_user.id,
            action="skill",
            skill_id=skill_id,
        )

    except Exception:
        logger.exception("PvP skill execution failed")
        await callback.answer(
            "اجرای مهارت با خطا روبه‌رو شد؛ گزارش ربات را بررسی کن.",
            show_alert=True,
        )
        return

    if not result["ok"]:
        await callback.answer(
            result["message"],
            show_alert=True,
        )
        return

    updated = result["battle"]

    displayed = await _edit_battle_panel(
        callback,
        updated,
        result["action_text"],
    )

    if not updated["finished"]:
        _schedule_turn_timer(updated)
    else:
        _cancel_turn_timer(battle_id)

    await callback.answer(
        "مهارت اجرا شد."
        if displayed
        else "مهارت اجرا شد، اما پنل به‌روزرسانی نشد.",
        show_alert=not displayed,
    )


@router.callback_query(F.data.startswith("pvp:potions:"))
async def pvp_potions_handler(callback: CallbackQuery) -> None:
    battle_id = callback.data.rsplit(":", 1)[-1]
    battle = await _validate_turn(callback, battle_id)

    if battle is None:
        return

    own = (
        "player1"
        if callback.from_user.id == battle["player1_id"]
        else "player2"
    )

    if battle[f"{own}_hp"] >= battle[f"{own}_max_hp"]:
        await callback.answer(
            "❤️ جانت کامل است؛ معجون مصرف نکن.",
            show_alert=True,
        )
        return

    if battle[f"{own}_heals_turn"] >= 2:
        await callback.answer(
            "🧪 در این نوبت ۲ بار درمان کرده‌ای.",
            show_alert=True,
        )
        return

    if battle[f"{own}_heals_total"] >= 5:
        await callback.answer(
            "🧪 سقف ۵ بار درمان این مبارزه را استفاده کرده‌ای.",
            show_alert=True,
        )
        return

    potions = await get_pvp_healing_potions(
        battle_id,
        callback.from_user.id,
    )

    if not potions:
        await callback.answer(
            "🧪 معجون سلامتی قابل استفاده‌ای در صندوقچه‌ات نداری.",
            show_alert=True,
        )
        return

    if callback.message is None:
        await callback.answer()
        return

    try:
        await callback.message.edit_text(
            "🧪 <b>انتخاب معجون</b>\n\n"
            f"❤️ HP فعلی: {battle[f'{own}_hp']}/{battle[f'{own}_max_hp']}\n"
            f"🧪 درمان این نوبت: {battle[f'{own}_heals_turn']}/2\n"
            f"🧪 کل درمان‌ها: {battle[f'{own}_heals_total']}/5\n\n"
            "معجون را از موجودی واقعی شخصیتت انتخاب کن:",
            reply_markup=pvp_potions_keyboard(battle_id, potions),
            parse_mode="HTML",
        )
        await callback.answer()

    except Exception:
        logger.exception("Failed to show PvP potions")
        await callback.answer(
            "نمایش معجون‌ها ناموفق بود.",
            show_alert=True,
        )


@router.callback_query(F.data.startswith("pvp:potion:"))
async def pvp_potion_handler(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")

    if len(parts) != 4:
        await callback.answer(
            "درخواست معجون نامعتبر است.",
            show_alert=True,
        )
        return

    _, _, battle_id, item_text = parts

    try:
        item_id = int(item_text)
    except (TypeError, ValueError):
        await callback.answer(
            "شناسه معجون نامعتبر است.",
            show_alert=True,
        )
        return

    battle = await _validate_turn(callback, battle_id)

    if battle is None:
        return

    result = await perform_pvp_action(
        battle_id=battle_id,
        telegram_id=callback.from_user.id,
        action="potion",
        item_id=item_id,
    )

    if not result["ok"]:
        await callback.answer(
            result["message"],
            show_alert=True,
        )
        return

    updated = result["battle"]

    displayed = await _edit_battle_panel(
        callback,
        updated,
        result["action_text"],
    )

    # مصرف معجون نوبت بازیکن را تمام نمی‌کند.
    _schedule_turn_timer(updated)

    await callback.answer(
        "🧪 معجون مصرف شد."
        if displayed
        else "معجون مصرف شد، اما پنل به‌روزرسانی نشد.",
        show_alert=not displayed,
    )


@router.callback_query(F.data.startswith("pvp:back:"))
async def pvp_back_handler(callback: CallbackQuery) -> None:
    battle_id = callback.data.rsplit(":", 1)[-1]
    battle = await get_pvp_battle(battle_id)

    if battle is None:
        await callback.answer(
            "❌ این مبارزه دیگر فعال نیست.",
            show_alert=True,
        )
        return

    if callback.from_user.id not in (
        battle["player1_id"],
        battle["player2_id"],
    ):
        await callback.answer(
            "⛔ شما عضو این مبارزه نیستید.",
            show_alert=True,
        )
        return

    if battle["finished"]:
        if callback.message:
            await _edit_battle_panel(callback, battle)

        await callback.answer("🏁 این مبارزه تمام شده است.")
        return

    deadline = float(battle.get("turn_deadline", 0) or 0)

    if deadline <= time.time():
        expired = await expire_pvp_turn(
            battle_id,
            expected_deadline=deadline,
        )

        if expired is not None:
            battle, action_text = expired
            await _edit_battle_panel(
                callback,
                battle,
                action_text,
            )
            _schedule_turn_timer(battle)
            await callback.answer(
                "⌛ نوبت منقضی شد و پنل به‌روز شد."
            )
            return

        battle = await get_pvp_battle(battle_id)

        if battle is None:
            await callback.answer(
                "❌ این مبارزه دیگر فعال نیست.",
                show_alert=True,
            )
            return

    if callback.message is None:
        await callback.answer()
        return

    try:
        await callback.message.edit_text(
            _battle_text(battle),
            reply_markup=(
                None
                if battle["finished"]
                else pvp_battle_keyboard(battle_id)
            ),
            parse_mode="HTML",
        )
        await callback.answer()

    except Exception:
        logger.exception("Failed to return to PvP panel")
        await callback.answer(
            "بازگشت ناموفق بود.",
            show_alert=True,
        )
PET_PHRASE_RE = re.compile(r"^[\w\u0600-\u06FF]{2,24}$", re.UNICODE)
RESERVED_PET_PHRASES = {"حمله", "mypet", "تنظیم", "استارت", "start", "help", "لغو"}


async def _get_active_pet_row(telegram_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(CharacterPet, Pet, Character)
            .join(Pet, Pet.id == CharacterPet.pet_id)
            .join(Character, Character.id == CharacterPet.character_id)
            .where(Character.telegram_id == telegram_id, CharacterPet.active.is_(True))
            .limit(1)
        )
        return result.first()


class ActivePetAttackPhraseFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if message.from_user is None or message.from_user.is_bot or not message.text:
            return False
        phrase = message.text.strip()
        if not phrase or phrase.startswith("/"):
            return False
        async with AsyncSessionLocal() as session:
            match = await session.scalar(
                select(CharacterPet.id)
                .join(Character, Character.id == CharacterPet.character_id)
                .where(
                    Character.telegram_id == message.from_user.id,
                    CharacterPet.active.is_(True),
                    CharacterPet.pet_attack_phrase == phrase,
                )
                .limit(1)
            )
        return match is not None


@router.message(Command("mypet"))
async def mypet_help(message: Message) -> None:
    if message.from_user is None:
        return
    active = await _get_active_pet_row(message.from_user.id)
    if not active:
        await message.reply("🐾 هنوز پت فعالی نداری. ابتدا از بخش پت‌ها یک پت تهیه و فعال کن.")
        return
    pet_row, pet, _character = active
    now = datetime.utcnow()
    started = pet_row.pet_attack_window_started_at
    uses = int(pet_row.pet_attack_uses or 0)
    if started is None or now - started >= PET_ATTACK_WINDOW:
        remaining_text = "آماده؛ سهمیهٔ ۲۴ ساعته از اولین حمله شروع می‌شود."
        uses = 0
    elif uses < PET_ATTACKS_PER_WINDOW:
        remaining_text = f"{PET_ATTACKS_PER_WINDOW - uses} حمله باقی مانده در بازهٔ ۲۴ ساعته."
    else:
        seconds = max(0, int((started + PET_ATTACK_WINDOW - now).total_seconds()))
        remaining_text = f"سهمیه پر شده؛ بازگشت حمله‌ها تا {seconds // 3600} ساعت و {(seconds % 3600) // 60} دقیقهٔ دیگر."
    phrase = pet_row.pet_attack_phrase or "تنظیم نشده"
    await message.reply(
        f"🐾 <b>پیوند پت اِلدوریا</b>\n\n"
        f"✨ پت فعال: <b>{html.escape(pet.name)}</b> · Lv.{min(100, int(pet_row.level or 1))}\n"
        f"🗝 کلمهٔ حملهٔ اختصاصی: <code>{html.escape(phrase)}</code>\n"
        f"⚔️ حمله با پت: حداکثر ۳ بار در هر ۲۴ ساعت\n"
        f"⏳ وضعیت سهمیه: {html.escape(remaining_text)}\n\n"
        "<b>راهنما</b>\n"
        "۱. برای تعیین کلمهٔ اختصاصی بنویس: <code>تنظیم حمله پت < عبارت ></code>\n"
        "۲. در گروه روی پیام بازیکن هدف ریپلای کن و کلمهٔ اختصاصی پتت را بفرست.\n"
        "۳. کلمهٔ عمومی <code>حمله</code> همچنان حملهٔ عادی قهرمان را اجرا می‌کند.\n\n"
        "قدرت پایهٔ حملهٔ پت با سطحش بالا می‌رود؛ در Lv.100 به حدود ۱۱۰٪ حملهٔ قهرمان می‌رسد.",
        parse_mode="HTML",
    )


@router.message(F.text.regexp(r"(?i)^\s*تنظیم\s+حمله\s+پت\s+([^\s]+)\s*$"))
async def set_pet_attack_phrase(message: Message) -> None:
    if message.from_user is None or message.from_user.is_bot:
        return
    match = re.match(r"(?i)^\s*تنظیم\s+حمله\s+پت\s+([^\s]+)\s*$", message.text or "")
    if not match:
        return
    phrase = match.group(1).strip()
    if not PET_PHRASE_RE.fullmatch(phrase) or phrase.lower() in RESERVED_PET_PHRASES or phrase.startswith("/"):
        await message.reply("❌ کلمه باید یک واژهٔ ۲ تا ۲۴ حرفی باشد و نباید با فرمان‌های رزروشده تداخل داشته باشد.")
        return
    async with AsyncSessionLocal() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == message.from_user.id))
        if character is None:
            await message.reply("ابتدا با /start شخصیتت را بساز.")
            return
        pet_row = await session.scalar(
            select(CharacterPet)
            .where(CharacterPet.character_id == character.id, CharacterPet.active.is_(True))
            .with_for_update()
        )
        if pet_row is None:
            await message.reply("🐾 برای تنظیم فرمان، ابتدا یک پت را فعال کن.")
            return
        pet_row.pet_attack_phrase = phrase
        pet_name = await session.scalar(select(Pet.name).where(Pet.id == pet_row.pet_id))
        await session.commit()
    await message.reply(
        f"🗝 کلمهٔ حملهٔ پت «{html.escape(str(pet_name or 'پت'))}» تنظیم شد: <code>{html.escape(phrase)}</code>\n\n"
        "برای حمله، در گروه روی پیام بازیکن هدف ریپلای کن و همین کلمه را بفرست. هر ۲۴ ساعت ۳ حمله با پت مجاز است.",
        parse_mode="HTML",
    )


@router.message(ActivePetAttackPhraseFilter())
async def direct_pet_attack_phrase_handler(message: Message) -> None:
    if message.chat.type not in {"group", "supergroup"}:
        await message.reply("🐾 حملهٔ پت فقط در گروه و با ریپلای روی پیام هدف انجام می‌شود.")
        return
    if message.from_user is None or message.from_user.is_bot:
        return
    replied = message.reply_to_message
    if replied is None or replied.from_user is None:
        await message.reply("🎯 برای حملهٔ پت، روی پیام بازیکن هدف ریپلای کن و کلمهٔ اختصاصی پتت را بفرست.")
        return
    target = replied.from_user
    if target.is_bot or target.id == message.from_user.id:
        await message.reply("🛡️ این هدف برای حملهٔ پت معتبر نیست.")
        return
    try:
        result = await direct_pet_attack(message.from_user.id, target.id)
    except Exception:
        logger.exception("Direct pet PvP attack failed")
        await message.reply("❌ حملهٔ پت ناموفق بود؛ جزئیات در گزارش ربات ثبت شد.")
        return
    if not result.get("ok"):
        await message.reply(str(result.get("message", "❌ حملهٔ پت انجام نشد.")))
        return
    attacker_name = html.escape(str(result["attacker_name"]))
    target_name = html.escape(str(result["target_name"]))
    pet_name = html.escape(str(result["pet_name"]))
    critical_line = "\n💥 <b>ضربهٔ بحرانی!</b>" if result["critical"] else ""
    pet_ability_line = ""
    if result.get("attacker_pet_ability"):
        pet_ability_line += f"\n✨ توانایی پت مهاجم: {html.escape(str(result['attacker_pet_ability']))}"
    if result.get("target_pet_ability"):
        pet_ability_line += f"\n🛡️ توانایی پت هدف: {html.escape(str(result['target_pet_ability']))}"
    text = (
        f"🐾 🎯 <b>{attacker_name}</b> <i>({html.escape(str(result.get('attacker_title') or 'شاگرد اِلدوریا'))})</i> و پت او «{pet_name}» ➜ "
        f"<b>{target_name}</b> <i>({html.escape(str(result.get('target_title') or 'شاگرد اِلدوریا'))})</i>\n\n"
        f"💥 پت در سطح {int(result['pet_level'])} ضربه زد و <b>{int(result['damage']):,} آسیب</b> وارد کرد!{critical_line}\n"
        f"📊 ATK قهرمان: {int(result.get('attacker_stats', {}).get('attack', 0))} · DEF هدف: {int(result.get('target_stats', {}).get('defense', 0))}\n"
        f"❤️ سلامتی باقی‌ماندهٔ {target_name}: <b>{int(result['target_hp']):,} / {int(result['target_max_hp']):,}</b>\n"
        f"🪙 پاداش ضربه (بر اساس آسیب): <b>+{int(result['attack_reward']):,} طلا</b>\n"
        f"🐾 حمله‌های باقی‌مانده با پت: <b>{int(result['uses_left'])}/3</b> در بازهٔ ۲۴ ساعته"
        f"{pet_ability_line}"
    )
    if result["killed"]:
        text += (
            f"\n\n☠️ <b>{target_name}</b> شکست خورد!"
            f"\n🎁 غنیمت منتقل‌شده: <b>+{int(result['loot']):,} طلا</b>؛ از دارایی حریف کسر شد."
            "\n⏳ هدف تا ۱۰ دقیقه از نبرد محروم است و سپس با HP و مانای کامل احیا می‌شود."
        )
    if int(result.get("bounty_reward", 0)) > 0:
        text += f"\n🏹 جایزهٔ شکار: <b>+{int(result['bounty_reward']):,} طلا</b>"
    await message.reply(text, parse_mode="HTML")


@router.message(Command("bounty"))
async def bounty_command(message: Message) -> None:
    """Place an escrowed gold bounty by replying to a player's message: /bounty 5000."""
    if message.from_user is None or message.from_user.is_bot:
        return
    parts = (message.text or "").split()
    replied = message.reply_to_message
    if len(parts) == 1:
        if replied and replied.from_user and not replied.from_user.is_bot:
            await message.reply(
                "🏹 برای تعیین جایزه روی پیام هدف ریپلای کن و بنویس: <code>/bounty 5000</code>\n"
                "حداقل جایزه: ۱۰۰۰ گلد؛ مبلغ از دارایی تو کسر و تا زمان شکار نگهداری می‌شود.",
                parse_mode="HTML",
            )
            return
        async with AsyncSessionLocal() as session:
            rows = (await session.execute(
                select(PvpBounty, Character.name)
                .join(Character, Character.id == PvpBounty.target_character_id)
                .where(PvpBounty.status == "active")
                .order_by(PvpBounty.amount.desc()).limit(10)
            )).all()
        if not rows:
            await message.reply(
                "🏹 در حال حاضر هیچ جایزهٔ فعالی برای شکار بازیکنان ثبت نشده است.\n"
                "برای ثبت جایزه، روی پیام هدف ریپلای کن و بنویس <code>/bounty 5000</code>.",
                parse_mode="HTML",
            )
            return
        lines = ["🏹 <b>تابلوی جایزه‌های فعال اِلدوریا</b>"]
        for row, target_name in rows:
            lines.append(f"• {html.escape(str(target_name))} — <b>{int(row.amount):,} طلا</b>")
        await message.reply("\n".join(lines), parse_mode="HTML")
        return
    if message.chat.type not in {"group", "supergroup"} or replied is None or replied.from_user is None or replied.from_user.is_bot:
        await message.reply("🎯 در گروه روی پیام بازیکن ریپلای کن و بنویس: <code>/bounty 5000</code>", parse_mode="HTML")
        return
    try:
        amount = int(parts[1])
    except (ValueError, IndexError):
        await message.reply("❌ مبلغ معتبر نیست. نمونه: <code>/bounty 5000</code>", parse_mode="HTML")
        return
    if amount < 1000 or amount > 100_000_000:
        await message.reply("❌ مبلغ جایزه باید بین ۱٬۰۰۰ تا ۱۰۰٬۰۰۰٬۰۰۰ گلد باشد.")
        return
    if replied.from_user.id == message.from_user.id:
        await message.reply("❌ نمی‌توانی برای شکار خودت جایزه تعیین کنی.")
        return
    async with AsyncSessionLocal() as session:
        sponsor = await session.scalar(select(Character).where(Character.telegram_id == message.from_user.id).with_for_update())
        target = await session.scalar(select(Character).where(Character.telegram_id == replied.from_user.id).with_for_update())
        if sponsor is None or target is None:
            await message.reply("❌ هر دو بازیکن باید ابتدا با /start شخصیت اِلدوریا ساخته باشند.")
            return
        if int(sponsor.gold or 0) < amount:
            await message.reply(f"💰 گلد کافی نداری. موجودی تو: {int(sponsor.gold or 0):,} گلد.")
            return
        sponsor.gold = int(sponsor.gold or 0) - amount
        session.add(PvpBounty(target_character_id=target.id, sponsor_character_id=sponsor.id, amount=amount, status="active", created_at=datetime.utcnow()))
        await session.commit()
        target_name = html.escape(target.name)
    await message.reply(
        f"🏹 برای شکار <b>{target_name}</b> جایزهٔ <b>{amount:,} طلا</b> ثبت شد!\n"
        "💰 مبلغ از موجودی تو کسر و در خزانهٔ جایزه نگهداری می‌شود؛ بازیکنی که او را در PvP شکست دهد، جایزه را دریافت می‌کند.",
        parse_mode="HTML",
    )
