from aiogram.fsm.state import State, StatesGroup


class FanArtStates(StatesGroup):
    waiting_receipt = State()

    add_image = State()
    add_name = State()
    add_description = State()
    add_rarity = State()
    add_price = State()
    add_value_gold = State()
    add_limited = State()
    add_stock = State()


class FanArtAdminStates(StatesGroup):
    reject_reason = State()
    search_order_code = State()