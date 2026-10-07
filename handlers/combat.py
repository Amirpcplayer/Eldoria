from aiogram import F, Router
from aiogram.types import CallbackQuery

from keyboards.adventure import adventure_main_keyboard
from keyboards.combat import (
    combat_keyboard,
    combat_potions_keyboard,
    combat_skills_keyboard,
)
from services.combat_service import (
    create_battle,
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
    """
    Battle ممکن است enemy_name را نداشته باشد.
    نام Variant یا سایر کلیدهای موجود را به‌صورت امن بررسی می‌کنیم.
    """

    possible_names = (
        battle.get("enemy_name"),
        battle.get("enemy_variant"),
        battle.get("monster_name"),
        battle.get("variant_name"),
    )

    for name in possible_names:
        if name:
            return str(name)

    return "دشمن"


async def show_battle(
    callback: CallbackQuery,
    battle: dict,
    player_damage: int | None = None,
    enemy_damage: int | None = None,
    action_text: str | None = None,
) -> None:
    combat_log = ""

    if action_text:
        combat_log += f"\n{action_text}"

    if player_damage is not None:
        combat_log += (
            f"\n⚔️ آسیب تو: <b>{player_damage}</b>"
        )

    if enemy_damage is not None:
        combat_log += (
            f"\n💥 آسیب دشمن: <b>{enemy_damage}</b>"
        )

    enemy_name = get_enemy_display_name(battle)

    text = (
        "⚔️ <b>مبارزه</b>\n\n"
        "👤 <b>تو</b>\n"
        f"❤️ HP: {battle['player_hp']}/{battle['player_max_hp']}\n"
        f"🔵 Mana: "
        f"{battle['player_mana']}/{battle['player_max_mana']}\n\n"
        f"👹 <b>{enemy_name}</b>\n"
        f"❤️ HP: {battle['enemy_hp']}/{battle['enemy_max_hp']}\n"
        f"⚔️ Attack: {battle['enemy_attack']}\n"
        f"🛡️ Defense: {battle['enemy_defense']}"
    )

    if combat_log:
        text += f"\n{combat_log}"

    text += f"\n\n🔄 نوبت: {battle['turn']}"

    if battle.get("defending", False):
        text += "\n\n🛡️ حالت دفاع فعال است."

    await callback.message.edit_text(
        text,
        reply_markup=combat_keyboard(
            battle["battle_id"]
        ),
        parse_mode="HTML",
    )


async def show_defeat(
    callback: CallbackQuery,
    battle: dict,
    enemy_damage: int | None = None,
) -> None:
    damage_text = ""

    if enemy_damage is not None:
        damage_text = (
            f"\n💥 آسیب نهایی دشمن: "
            f"<b>{enemy_damage}</b>\n"
        )

    enemy_name = get_enemy_display_name(battle)

    text = (
        "💀 <b>شکست خوردی!</b>\n\n"
        f"👹 دشمن: {enemy_name}\n"
        f"{damage_text}\n"
        "❤️ HP تو به صفر رسید.\n"
        "هیچ پاداشی دریافت نکردی."
    )

    await callback.message.edit_text(
        text,
        reply_markup=adventure_main_keyboard(),
        parse_mode="HTML",
    )


async def show_victory(
    callback: CallbackQuery,
    battle: dict,
    damage: int,
) -> None:
    (
        success,
        xp,
        skill_xp,
        gold,
        levels_gained,
    ) = await finish_victory(
        battle["battle_id"]
    )

    if not success:
        await callback.message.edit_text(
            "⚠️ دریافت پاداش با مشکل مواجه شد.\n"
            "لطفاً دوباره تلاش کن.",
            reply_markup=adventure_main_keyboard(),
            parse_mode="HTML",
        )
        return

    level_text = ""

    if levels_gained > 0:
        level_text = (
            f"\n🎉 Level Up: +{levels_gained}"
        )

    enemy_name = get_enemy_display_name(battle)

    text = (
        "🏆 <b>پیروزی!</b>\n\n"
        f"👹 {enemy_name} شکست خورد!\n\n"
        f"⚔️ آسیب نهایی تو: <b>{damage}</b>\n\n"
        f"✨ XP: +{xp}\n"
        f"🔮 Skill XP: +{skill_xp}\n"
        f"💰 Gold: +{gold}"
        f"{level_text}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=adventure_main_keyboard(),
        parse_mode="HTML",
    )


async def validate_battle_owner(
    callback: CallbackQuery,
    battle_id: str,
) -> dict | None:
    battle = await get_battle(
        battle_id
    )

    if battle is None:
        await callback.answer(
            "❌ این مبارزه دیگر فعال نیست.",
            show_alert=True,
        )
        return None

    if battle["telegram_id"] != callback.from_user.id:
        await callback.answer(
            "❌ این مبارزه متعلق به شما نیست.",
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


# ============================================================
# ENEMY TURN
# ============================================================

async def process_enemy_turn(
    callback: CallbackQuery,
    battle_id: str,
    player_damage: int,
    action_text: str,
) -> tuple[bool, dict | None]:

    (
        enemy_success,
        enemy_damage,
        defeated,
        battle,
    ) = await enemy_turn(
        battle_id
    )

    if not enemy_success or battle is None:
        await callback.answer(
            "⚠️ نوبت دشمن با مشکل مواجه شد.",
            show_alert=True,
        )
        return False, None

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

        return True, battle

    await show_battle(
        callback,
        battle,
        player_damage=player_damage,
        enemy_damage=enemy_damage,
        action_text=action_text,
    )

    await callback.answer(
        f"⚔️ آسیب تو: {player_damage} | "
        f"💥 آسیب دشمن: {enemy_damage}"
    )

    return True, battle


# ============================================================
# START COMBAT
# ============================================================

@router.callback_query(
    F.data.startswith("adventure:fight:")
)
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
            "❌ دشمن نامعتبر است.",
            show_alert=True,
        )
        return

    success, message, battle = await create_battle(
        callback.from_user.id,
        enemy_id,
    )

    if not success or battle is None:
        await callback.answer(
            message,
            show_alert=True,
        )
        return

    enemy_name = get_enemy_display_name(battle)

    await callback.message.edit_text(
        (
            "⚔️ <b>مبارزه آغاز شد!</b>\n\n"
            f"👹 دشمن: {enemy_name}\n"
            f"❤️ HP دشمن: "
            f"{battle['enemy_hp']}/"
            f"{battle['enemy_max_hp']}\n\n"
            f"❤️ HP تو: "
            f"{battle['player_hp']}/"
            f"{battle['player_max_hp']}\n"
            f"🔵 Mana: "
            f"{battle['player_mana']}/"
            f"{battle['player_max_mana']}"
        ),
        reply_markup=combat_keyboard(
            battle["battle_id"]
        ),
        parse_mode="HTML",
    )

    await callback.answer(
        "⚔️ مبارزه شروع شد!"
    )


# ============================================================
# ATTACK
# ============================================================

@router.callback_query(
    F.data.startswith("combat:attack:")
)
async def combat_attack_handler(
    callback: CallbackQuery,
) -> None:
    battle_id = callback.data.split(":")[-1]

    battle = await validate_battle_owner(
        callback,
        battle_id,
    )

    if battle is None:
        return

    (
        success,
        damage,
        victory,
        battle,
    ) = await player_attack(
        battle_id
    )

    if not success or battle is None:
        await callback.answer(
            "❌ حمله انجام نشد.",
            show_alert=True,
        )
        return

    if victory:
        await show_victory(
            callback,
            battle,
            damage,
        )

        await callback.answer(
            f"⚔️ آسیب تو: {damage}"
        )
        return

    await process_enemy_turn(
        callback,
        battle_id,
        player_damage=damage,
        action_text="⚔️ حمله انجام شد.",
    )


# ============================================================
# SKILLS MENU
# ============================================================

@router.callback_query(
    F.data.startswith("combat:skills:")
)
async def combat_skills_handler(
    callback: CallbackQuery,
) -> None:
    battle_id = callback.data.split(":")[-1]

    battle = await validate_battle_owner(
        callback,
        battle_id,
    )

    if battle is None:
        return

    character = await get_character(
        callback.from_user.id
    )

    if character is None:
        await callback.answer(
            "❌ شخصیت پیدا نشد.",
            show_alert=True,
        )
        return

    skills = await get_character_skills(
        character.id
    )

    if not skills:
        await callback.answer(
            "⚠️ هیچ مهارتی در دسترس نیست.",
            show_alert=True,
        )
        return

    text = (
        "🔮 <b>مهارت‌ها</b>\n\n"
        f"🔵 Mana: "
        f"{battle['player_mana']}/"
        f"{battle['player_max_mana']}\n\n"
        "مهارت موردنظر را انتخاب کن:"
    )

    await callback.message.edit_text(
        text,
        reply_markup=combat_skills_keyboard(
            battle_id,
            skills,
        ),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# USE SKILL
# ============================================================

@router.callback_query(
    F.data.startswith("combat:skill:")
)
async def combat_skill_handler(
    callback: CallbackQuery,
) -> None:
    parts = callback.data.split(":")

    if len(parts) != 4:
        await callback.answer(
            "❌ درخواست نامعتبر است.",
            show_alert=True,
        )
        return

    battle_id = parts[2]

    try:
        skill_id = int(parts[3])
    except ValueError:
        await callback.answer(
            "❌ مهارت نامعتبر است.",
            show_alert=True,
        )
        return

    battle = await validate_battle_owner(
        callback,
        battle_id,
    )

    if battle is None:
        return

    (
        success,
        message,
        damage,
        victory,
        battle,
    ) = await player_skill(
        battle_id,
        skill_id,
    )

    if not success or battle is None:
        await callback.answer(
            message,
            show_alert=True,
        )
        return

    if victory:
        await show_victory(
            callback,
            battle,
            damage,
        )

        await callback.answer(
            f"🔮 آسیب مهارت تو: {damage}"
        )
        return

    await process_enemy_turn(
        callback,
        battle_id,
        player_damage=damage,
        action_text=message,
    )


# ============================================================
# POTIONS MENU
# ============================================================

@router.callback_query(
    F.data.startswith("combat:potions:")
)
async def combat_potions_handler(
    callback: CallbackQuery,
) -> None:
    battle_id = callback.data.split(":")[-1]

    battle = await validate_battle_owner(
        callback,
        battle_id,
    )

    if battle is None:
        return

    if battle["player_hp"] >= battle["player_max_hp"]:
        await callback.answer(
            "❤️ HP شما کاملاً پر است.",
            show_alert=True,
        )
        return

    potions = await get_healing_potions(
        battle["character_id"]
    )

    if not potions:
        await callback.answer(
            "🧪 هیچ معجون سلامتی در صندوقچه شما وجود ندارد.",
            show_alert=True,
        )
        return

    text = (
        "🧪 <b>معجون‌ها</b>\n\n"
        f"❤️ HP فعلی: "
        f"{battle['player_hp']}/"
        f"{battle['player_max_hp']}\n\n"
        "معجون موردنظر را انتخاب کن:"
    )

    await callback.message.edit_text(
        text,
        reply_markup=combat_potions_keyboard(
            battle_id,
            potions,
        ),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# USE POTION
# ============================================================

@router.callback_query(
    F.data.startswith("combat:potion:")
)
async def combat_potion_handler(
    callback: CallbackQuery,
) -> None:
    parts = callback.data.split(":")

    if len(parts) != 4:
        await callback.answer(
            "❌ درخواست نامعتبر است.",
            show_alert=True,
        )
        return

    battle_id = parts[2]

    try:
        item_id = int(parts[3])
    except ValueError:
        await callback.answer(
            "❌ معجون نامعتبر است.",
            show_alert=True,
        )
        return

    battle = await validate_battle_owner(
        callback,
        battle_id,
    )

    if battle is None:
        return

    (
        success,
        message,
        healed,
        updated_battle,
    ) = await use_healing_potion(
        battle_id,
        item_id,
    )

    if not success or updated_battle is None:
        await callback.answer(
            message,
            show_alert=True,
        )
        return

    await show_battle(
        callback,
        updated_battle,
    )

    await callback.answer(
        f"🧪 مقدار HP بازیابی‌شده: +{healed}"
    )


# ============================================================
# FLEE
# ============================================================

@router.callback_query(
    F.data.startswith("combat:flee:")
)
async def combat_flee_handler(
    callback: CallbackQuery,
) -> None:
    battle_id = callback.data.split(":")[-1]

    battle = await validate_battle_owner(
        callback,
        battle_id,
    )

    if battle is None:
        return

    success = await flee_battle(
        battle_id
    )

    if not success:
        await callback.answer(
            "❌ خروج از مبارزه انجام نشد.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "🏃 <b>از مبارزه فرار کردی.</b>\n\n"
        "هیچ پاداشی دریافت نکردی.",
        reply_markup=adventure_main_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer(
        "🏃 از مبارزه خارج شدی."
    )


# ============================================================
# BACK TO BATTLE
# ============================================================

@router.callback_query(
    F.data.startswith("combat:back:")
)
async def combat_back_handler(
    callback: CallbackQuery,
) -> None:
    battle_id = callback.data.split(":")[-1]

    battle = await validate_battle_owner(
        callback,
        battle_id,
    )

    if battle is None:
        return

    await show_battle(
        callback,
        battle,
    )

    await callback.answer()