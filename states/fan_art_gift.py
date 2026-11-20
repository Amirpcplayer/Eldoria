from aiogram.fsm.state import State, StatesGroup


class FanArtGiftStates(StatesGroup):
    # روش اول: ساخت فن‌آرت و گیفت مستقیم
    create_image = State()
    create_name = State()
    create_description = State()
    create_rarity = State()
    create_player = State()

    # روش دوم: گیفت فن‌آرت موجود در شاپ
    shop_player = State()
    shop_rarity = State()
    shop_art = State()

    # مرحله مشترک تأیید
    confirm_gift = State()