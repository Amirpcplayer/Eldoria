from aiogram.fsm.state import State, StatesGroup


class CharacterCreation(StatesGroup):
    waiting_for_name = State()
    waiting_for_gender = State()


class PlayerTrade(StatesGroup):
    waiting_for_target = State()
    waiting_for_price = State()
