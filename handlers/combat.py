from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from keyboards.adventure import adventure_main_keyboard
from keyboards.combat import (
    combat_keyboard,
    combat_potions_keyboard,
    combat_skills_keyboard,
)
from middlewares.panel_owner import protect_keyboard
from database.redis import redis
from services.combat_service import (
    create_battle,
    delete_battle,
    enemy_turn,
    finish_victory,
    flee_battle,
    get_battle,
    get_character,
    get_character_skills,
    get_healing_potions,
    player_attack,
    player_skill,
    use_healing_potion,
)

router = Router()


# ============================================================
# HELPERS
# ============================================================

def get_enemy_display_name(battle: dict) -> str:
    for name in (
        battle.get("enemy_name"),
        battle.get("enemy_variant"),
        battle.get("monster_name"),
        battle.get("variant_name"),
    ):
        if name:
            return str(name)

    return "دشمن"


async def render_battle_panel(
    callback: CallbackQuery,
    text: str,
    reply_markup,
) -> bool:
    """نمایش پنل؛ اگر افزودن پیشوند مالک باعث طولانی‌شدن callback شود،
    کیبورد اصلی استفاده می‌شود. هندلرهای مبارزه مالکیت بتل را بررسی می‌کنند.
    """

    message = callback.message

    if message is None:
        return False

    try:
        keyboard = protect_keyboard(
            reply_markup,
            callback.from_user.id,
        )
    except ValueError:
        # برخی callbackها با پیشوند مالک از محدودیت تلگرام عبور می‌کنند.
        # callbackهای مبارزه در هندلرها با مالکیت بتل اعتبارسنجی می‌شوند.
        keyboard = reply_markup

    if message.photo:
        try:
            await message.delete()
        except Exception:
            pass

        try:
            await message.answer(
                text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            return True
        except Exception:
            return False

    try:
        await message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        return True
    except Exception:
        pass

    try:
        await message.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        return True
    except Exception:
        return False


async def answer_display_error(
    callback: CallbackQuery,
) -> None:
    try:
        await callback.answer(
            "❌ نمایش پنل ناموفق بود. دوباره تلاش کن.",
            show_alert=True,
        )
    except Exception:
        pass


async def find_active_battle(
    telegram_id: int,
) -> dict | None:
    """پیدا کردن بتل فعال متعلق به همین بازیکن."""

    from database.redis import redis

    async for key in redis.scan_iter(
        match="eldoria:battle:*"
    ):
        if isinstance(key, bytes):
            key = key.decode("utf-8")

        if ":battle_reward:" in key:
            continue

        data = await redis.hgetall(key)

        if not data:
            continue

        stored_owner = data.get("telegram_id", 0)

        if isinstance(stored_owner, bytes):
            stored_owner = stored_owner.decode("utf-8")

        try:
            if int(stored_owner) != telegram_id:
                continue
        except (TypeError, ValueError):
            continue

        battle_id = key.rsplit(":", 1)[-1]
        battle = await get_battle(battle_id)

        if battle is not None:
            return battle

    return None


def build_battle_text(
    battle: dict,
    player_damage: int | None = None,
    enemy_damage: int | None = None,
    action_text: str | None = None,
) -> str:
    enemy_name = get_enemy_display_name(battle)

    text = (
        "⚔️ <b>مبارزه</b>\n\n"
        "👤 <b>تو</b>\n"
        f"❤️ HP: {battle['player_hp']}/"
        f"{battle['player_max_hp']}\n"
        f"🔵 Mana: {battle['player_mana']}/"
        f"{battle['player_max_mana']}\n\n"
        f"👹 <b>{enemy_name}</b>\n"
        f"❤️ HP: {battle['enemy_hp']}/"
        f"{battle['enemy_max_hp']}\n"
        f"⚔️ Attack: {battle['enemy_attack']}\n"
        f"🛡️ Defense: {battle['enemy_defense']}"
    )

    if action_text:
        text += f"\n\n{action_text}"

    if player_damage is not None:
        text += f"\n⚔️ آسیب تو: <b>{player_damage}</b>"

    if enemy_damage is not None:
        text += f"\n💥 آسیب دشمن: <b>{enemy_damage}</b>"

    text += f"\n\n🔄 نوبت: {battle['turn']}"

    if battle.get("defending", False):
        text += "\n\n🛡️ حالت دفاع فعال است."

    return text


async def show_battle(
    callback: CallbackQuery,
    battle: dict,
    player_damage: int | None = None,
    enemy_damage: int | None = None,
    action_text: str | None = None,
) -> bool:
    return await render_battle_panel(
        callback=callback,
        text=build_battle_text(
            battle,
            player_damage,
            enemy_damage,
            action_text,
        ),
        reply_markup=combat_keyboard(
            battle["battle_id"]
        ),
    )


async def show_defeat(
    callback: CallbackQuery,
    battle: dict,
    enemy_damage: int | None = None,
) -> bool:
    damage_text = ""

    if enemy_damage is not None:
        damage_text = (
            f"\n💥 آسیب نهایی دشمن: <b>{enemy_damage}</b>\n"
        )

    text = (
        "💀 <b>شکست خوردی!</b>\n\n"
        f"👹 دشمن: {get_enemy_display_name(battle)}\n"
        f"{damage_text}\n"
        "❤️ HP تو به صفر رسید.\n"
        "هیچ پاداشی دریافت نکردی."
    )

    await delete_battle(battle["battle_id"])

    return await render_battle_panel(
        callback,
        text,
        adventure_main_keyboard(),
    )


async def show_victory(
    callback: CallbackQuery,
    battle: dict,
    damage: int,
) -> bool:
    success, xp, skill_xp, gold, levels_gained = (
        await finish_victory(battle["battle_id"])
    )

    if not success:
        return await render_battle_panel(
            callback,
            (
                "⚠️ <b>دریافت پاداش ناموفق بود.</b>\n\n"
                "ثبت پاداش موفق نبود. لطفاً وضعیت بتل را بررسی کن."
            ),
            adventure_main_keyboard(),
        )

    level_text = (
        f"\n🎉 Level Up: +{levels_gained}"
        if levels_gained > 0
        else ""
    )
    drops = []
    try:
        import json
        raw_drops = await redis.get(f"eldoria:last_adventure_drops:{callback.from_user.id}")
        if raw_drops:
            drops = json.loads(raw_drops)
        await redis.delete(f"eldoria:last_adventure_drops:{callback.from_user.id}")
    except Exception:
        drops = []

    drop_text = "\n\n🎁 <b>آیتم‌های به‌دست‌آمده</b>\n" + ("\n".join(f"• {name}" for name in drops) if drops else "• این بار متریالی پیدا نشد.")
    text = (
        "🏆 <b>پیروزی!</b>\n\n"
        f"👹 {get_enemy_display_name(battle)} شکست خورد!\n\n"
        f"⚔️ آسیب نهایی تو: <b>{damage:,}</b>\n\n"
        f"✨ XP: +{xp:,}\n"
        f"🔮 Skill XP: +{skill_xp:,}\n"
        f"💰 Gold: +{gold:,}"
        f"{level_text}"
        f"{drop_text}"
    )

    return await render_battle_panel(
        callback,
        text,
        adventure_main_keyboard(),
    )


async def validate_battle_owner(
    callback: CallbackQuery,
    battle_id: str,
) -> dict | None:
    battle = await get_battle(battle_id)

    if battle is None:
        await callback.answer(
            "❌ این مبارزه دیگر فعال نیست.",
            show_alert=True,
        )
        return None

    try:
        owner_id = int(battle["telegram_id"])
    except (KeyError, TypeError, ValueError):
        await callback.answer(
            "❌ اطلاعات مالک مبارزه نامعتبر است.",
            show_alert=True,
        )
        return None

    if owner_id != callback.from_user.id:
        await callback.answer(
            "⛔ این مبارزه برای شما نیست!",
            show_alert=True,
        )
        return None

    if battle["player_hp"] <= 0:
        await callback.answer(
            "💀 قهرمان شما شکست خورده است.",
            show_alert=True,
        )
        return None

    if battle["enemy_hp"] <= 0:
        await callback.answer(
            "🏆 این دشمن قبلاً شکست خورده است.",
            show_alert=True,
        )
        return None

    return battle


async def process_enemy_turn(
    callback: CallbackQuery,
    battle_id: str,
    player_damage: int,
    action_text: str,
) -> None:
    enemy_success, enemy_damage, defeated, battle = (
        await enemy_turn(battle_id)
    )

    if not enemy_success or battle is None:
        await callback.answer(
            "⚠️ اجرای نوبت دشمن با مشکل مواجه شد.",
            show_alert=True,
        )
        return

    if defeated:
        await show_defeat(
            callback,
            battle,
            enemy_damage,
        )
        await callback.answer(
            f"⚔️ آسیب تو: {player_damage} | "
            f"💥 آسیب دشمن: {enemy_damage}"
        )
        return

    displayed = await show_battle(
        callback,
        battle,
        player_damage,
        enemy_damage,
        action_text,
    )

    if displayed:
        await callback.answer(
            f"⚔️ آسیب تو: {player_damage} | "
            f"💥 آسیب دشمن: {enemy_damage}"
        )
    else:
        await answer_display_error(callback)


# ============================================================
# START / RESUME COMBAT
# ============================================================

@router.callback_query(F.data.startswith("adventure:fight:"))
async def combat_start_handler(
    callback: CallbackQuery,
) -> None:
    parts = callback.data.split(":")

    if len(parts) != 3:
        await callback.answer(
            "❌ درخواست مبارزه نامعتبر است.",
            show_alert=True,
        )
        return

    try:
        enemy_id = int(parts[2])
    except ValueError:
        await callback.answer(
            "❌ شناسه دشمن نامعتبر است.",
            show_alert=True,
        )
        return

    try:
        success, message, battle = await create_battle(
            callback.from_user.id,
            enemy_id,
        )

        if not success or battle is None:
            existing_battle = await find_active_battle(
                callback.from_user.id
            )

            if existing_battle is not None:
                displayed = await show_battle(
                    callback,
                    existing_battle,
                    action_text="🔄 به مبارزه فعال قبلی برگشتی.",
                )

                if displayed:
                    await callback.answer(
                        "⚔️ مبارزه قبلی بازیابی شد."
                    )
                else:
                    await answer_display_error(callback)

                return

            await callback.answer(
                message or "❌ شروع مبارزه ناموفق بود.",
                show_alert=True,
            )
            return

        displayed = await show_battle(
            callback,
            battle,
            action_text="⚔️ مبارزه آغاز شد!",
        )

        if not displayed:
            await delete_battle(battle["battle_id"])
            await answer_display_error(callback)
            return

        await callback.answer("⚔️ مبارزه شروع شد!")

    except Exception:
        # خطا را در ترمینال ثبت می‌کنیم تا علت واقعی قابل تشخیص باشد.
        import logging

        logging.exception("Failed to start combat")
        await callback.answer(
            "❌ شروع مبارزه با خطا مواجه شد. ترمینال را بررسی کن.",
            show_alert=True,
        )


# ============================================================
# ATTACK
# ============================================================

@router.callback_query(F.data.startswith("combat:attack:"))
async def combat_attack_handler(
    callback: CallbackQuery,
) -> None:
    battle_id = callback.data.split(":")[-1]
    battle = await validate_battle_owner(callback, battle_id)

    if battle is None:
        return

    success, damage, victory, battle = await player_attack(battle_id)

    if not success or battle is None:
        await callback.answer(
            "❌ حمله انجام نشد.",
            show_alert=True,
        )
        return

    if victory:
        displayed = await show_victory(callback, battle, damage)

        if displayed:
            await callback.answer(f"⚔️ آسیب تو: {damage}")
        else:
            await answer_display_error(callback)

        return

    await process_enemy_turn(
        callback,
        battle_id,
        damage,
        "⚔️ حمله انجام شد.",
    )


# ============================================================
# SKILLS MENU
# ============================================================

@router.callback_query(F.data.startswith("combat:skills:"))
async def combat_skills_handler(
    callback: CallbackQuery,
) -> None:
    battle_id = callback.data.split(":")[-1]
    battle = await validate_battle_owner(callback, battle_id)

    if battle is None:
        return

    character = await get_character(callback.from_user.id)

    if character is None:
        await callback.answer(
            "❌ شخصیت پیدا نشد.",
            show_alert=True,
        )
        return

    skills = await get_character_skills(character.id)

    if not skills:
        await callback.answer(
            "⚠️ هیچ مهارتی در دسترس نیست.",
            show_alert=True,
        )
        return

    displayed = await render_battle_panel(
        callback,
        (
            "🔮 <b>مهارت‌ها</b>\n\n"
            f"🔵 Mana: {battle['player_mana']}/"
            f"{battle['player_max_mana']}\n\n"
            "مهارت موردنظر را انتخاب کن:"
        ),
        combat_skills_keyboard(battle_id, skills),
    )

    if displayed:
        await callback.answer()
    else:
        await answer_display_error(callback)


# ============================================================
# USE SKILL
# ============================================================

@router.callback_query(F.data.startswith("combat:skill:"))
async def combat_skill_handler(
    callback: CallbackQuery,
) -> None:
    parts = callback.data.split(":")

    if len(parts) != 4:
        await callback.answer(
            "❌ درخواست مهارت نامعتبر است.",
            show_alert=True,
        )
        return

    battle_id = parts[2]

    try:
        skill_id = int(parts[3])
    except ValueError:
        await callback.answer(
            "❌ شناسه مهارت نامعتبر است.",
            show_alert=True,
        )
        return

    if await validate_battle_owner(callback, battle_id) is None:
        return

    success, message, damage, victory, battle = await player_skill(
        battle_id,
        skill_id,
    )

    if not success or battle is None:
        await callback.answer(
            message or "❌ استفاده از مهارت ناموفق بود.",
            show_alert=True,
        )
        return

    if victory:
        displayed = await show_victory(callback, battle, damage)

        if displayed:
            await callback.answer(f"🔮 آسیب مهارت: {damage}")
        else:
            await answer_display_error(callback)

        return

    await process_enemy_turn(
        callback,
        battle_id,
        damage,
        message,
    )


# ============================================================
# POTIONS MENU
# ============================================================

@router.callback_query(F.data.startswith("combat:potions:"))
async def combat_potions_handler(
    callback: CallbackQuery,
) -> None:
    battle_id = callback.data.split(":")[-1]
    battle = await validate_battle_owner(callback, battle_id)

    if battle is None:
        return

    if battle["player_hp"] >= battle["player_max_hp"]:
        await callback.answer(
            "❤️ HP شما کاملاً پر است.",
            show_alert=True,
        )
        return

    potions = await get_healing_potions(
        battle["character_id"],
        max_hp=int(battle.get("player_max_hp", 100) or 100),
    )

    if not potions:
        await callback.answer(
            "🧪 معجون سلامتی در صندوقچه ندارید.",
            show_alert=True,
        )
        return

    displayed = await render_battle_panel(
        callback,
        (
            "🧪 <b>معجون‌ها</b>\n\n"
            f"❤️ HP فعلی: {battle['player_hp']}/"
            f"{battle['player_max_hp']}\n\n"
            "معجون موردنظر را انتخاب کن:"
        ),
        combat_potions_keyboard(battle_id, potions),
    )

    if displayed:
        await callback.answer()
    else:
        await answer_display_error(callback)


# ============================================================
# USE POTION
# ============================================================

@router.callback_query(F.data.startswith("combat:potion:"))
async def combat_potion_handler(
    callback: CallbackQuery,
) -> None:
    parts = callback.data.split(":")

    if len(parts) != 4:
        await callback.answer(
            "❌ درخواست معجون نامعتبر است.",
            show_alert=True,
        )
        return

    battle_id = parts[2]

    try:
        item_id = int(parts[3])
    except ValueError:
        await callback.answer(
            "❌ شناسه معجون نامعتبر است.",
            show_alert=True,
        )
        return

    if await validate_battle_owner(callback, battle_id) is None:
        return

    success, message, healed, updated_battle = (
        await use_healing_potion(
            battle_id,
            item_id,
        )
    )

    if not success or updated_battle is None:
        await callback.answer(
            message or "❌ استفاده از معجون ناموفق بود.",
            show_alert=True,
        )
        return

    displayed = await show_battle(
        callback,
        updated_battle,
    )

    if displayed:
        await callback.answer(
            f"🧪 مقدار HP بازیابی‌شده: +{healed}"
        )
    else:
        await answer_display_error(callback)


# ============================================================
# FLEE
# ============================================================

@router.callback_query(F.data.startswith("combat:flee:"))
async def combat_flee_handler(
    callback: CallbackQuery,
) -> None:
    battle_id = callback.data.split(":")[-1]

    if await validate_battle_owner(callback, battle_id) is None:
        return

    success = await flee_battle(battle_id)

    if not success:
        await callback.answer(
            "❌ خروج از مبارزه انجام نشد.",
            show_alert=True,
        )
        return

    displayed = await render_battle_panel(
        callback,
        "🏃 <b>از مبارزه خارج شدی.</b>\n\nهیچ پاداشی دریافت نکردی.",
        adventure_main_keyboard(),
    )

    if displayed:
        await callback.answer("🏃 از مبارزه خارج شدی.")
    else:
        await answer_display_error(callback)


# ============================================================
# BACK TO BATTLE
# ============================================================

@router.callback_query(F.data.startswith("combat:back:"))
async def combat_back_handler(
    callback: CallbackQuery,
) -> None:
    battle_id = callback.data.split(":")[-1]
    battle = await validate_battle_owner(callback, battle_id)

    if battle is None:
        return

    displayed = await show_battle(
        callback,
        battle,
    )

    if displayed:
        await callback.answer()
    else:
        await answer_display_error(callback)