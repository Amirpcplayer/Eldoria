from aiogram.fsm.state import State, StatesGroup


class CharacterCreation(StatesGroup):
    waiting_for_name = State()


class PlayerTrade(StatesGroup):
    waiting_for_target = State()
    waiting_for_price = State()