from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def skills_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📚 مهارت‌های من",
                    callback_data="skills:list",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✨ یادگیری مهارت",
                    callback_data="skills:learn",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬆️ ارتقای مهارت",
                    callback_data="skills:upgrade",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="menu:back",
                ),
            ],
        ]
    )


# ==================================================
# لیست «مهارت‌های من»
# ==================================================

def skills_list_keyboard(skills) -> InlineKeyboardMarkup:
    buttons = []

    for skill_name, skill_id in skills:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=skill_name,
                    callback_data=f"skill:details:{skill_id}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت به مهارت‌ها",
                callback_data="menu:skills",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


# ==================================================
# لیست «یادگیری مهارت»
# ==================================================

def learn_skills_keyboard(skills) -> InlineKeyboardMarkup:
    buttons = []

    for skill_name, skill_id, status in skills:

        if status == "available":
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"🟢 {skill_name}",
                        callback_data=f"learn:{skill_id}",
                    )
                ]
            )

        elif status == "locked":
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"🔒 {skill_name}",
                        callback_data="skill:locked",
                    )
                ]
            )

        elif status == "owned":
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"✅ {skill_name}",
                        callback_data=f"learned:details:{skill_id}",
                    )
                ]
            )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت به مهارت‌ها",
                callback_data="menu:skills",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


# ==================================================
# جزئیات مهارت از «مهارت‌های من»
# بدون دکمه ارتقا
# ==================================================

def my_skill_details_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت به مهارت‌های من",
                    callback_data="skills:list",
                )
            ],
        ]
    )


# ==================================================
# جزئیات مهارت از «یادگیری مهارت»
# بدون دکمه ارتقا
# ==================================================

def learned_skill_details_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت به یادگیری مهارت",
                    callback_data="skills:learn",
                )
            ],
        ]
    )


# ==================================================
# لیست مهارت‌های قابل ارتقا
# تنها مسیر ورود به پنل ارتقا
# ==================================================

def skill_upgrade_list_keyboard(skills) -> InlineKeyboardMarkup:
    buttons = []

    for skill_name, skill_id, level in skills:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"⬆️ {skill_name} • Lv.{level}",
                    callback_data=f"skill:upgrade:{skill_id}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت به مهارت‌ها",
                callback_data="menu:skills",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


# ==================================================
# تأیید ارتقای مهارت
# ==================================================

def skill_upgrade_confirm_keyboard(
    skill_id: int,
) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تأیید ارتقا",
                    callback_data=f"skill:upgrade_confirm:{skill_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ لغو",
                    callback_data="skills:upgrade",
                ),
            ],
        ]
    )