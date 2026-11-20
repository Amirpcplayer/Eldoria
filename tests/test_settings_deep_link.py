from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from handlers import start as start_module
from utils.telegram_links import get_bot_deep_link


class FakeMe:
    username = "WorldEldoriaTestBot"


class FakeBot:
    async def get_me(self):
        return FakeMe()


class FakeSession:
    def __init__(self, character):
        self.character = character

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def scalar(self, statement):
        return self.character


@pytest.mark.asyncio
async def test_settings_deep_link_points_to_current_bot_with_settings_payload():
    url = await get_bot_deep_link(FakeBot(), "settings")
    assert url == "https://t.me/WorldEldoriaTestBot?start=settings"


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["/start settings", "/start@WorldEldoriaTestBot settings"])
async def test_start_settings_payload_renders_settings_panel_for_existing_character(monkeypatch, text):
    character = SimpleNamespace(telegram_id=42, name="Hero")
    monkeypatch.setattr(start_module, "AsyncSessionLocal", lambda: FakeSession(character))
    monkeypatch.setattr(start_module, "recover_character_vitals", AsyncMock())

    from handlers import command_aliases
    render_panel = AsyncMock()
    monkeypatch.setattr(command_aliases, "render_command_panel", render_panel)

    state = SimpleNamespace(clear=AsyncMock())
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=42),
        chat=SimpleNamespace(type="private"),
        text=text,
        answer=AsyncMock(),
    )

    await start_module.start_handler(message, state)

    render_panel.assert_awaited_once_with(message, "settings")
    state.clear.assert_awaited_once()
    message.answer.assert_not_awaited()


@pytest.mark.asyncio
async def test_group_settings_click_sends_private_settings_panel_when_bot_chat_is_available(monkeypatch):
    from handlers import command_aliases

    character = SimpleNamespace(telegram_id=42, name="Hero")
    monkeypatch.setattr(command_aliases, "AsyncSessionLocal", lambda: FakeSession(character))
    monkeypatch.setattr(command_aliases, "get_language", AsyncMock(return_value="fa"))
    monkeypatch.setattr(command_aliases, "show_panel", AsyncMock())

    bot = FakeBot()
    bot.send_message = AsyncMock()
    callback = SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(type="group")),
        from_user=SimpleNamespace(id=42),
        bot=bot,
        answer=AsyncMock(),
    )

    await command_aliases.settings_menu_callback(callback)

    bot.send_message.assert_awaited_once()
    sent_kwargs = bot.send_message.await_args.kwargs
    assert sent_kwargs["chat_id"] == 42
    assert sent_kwargs["reply_markup"].inline_keyboard[0][0].callback_data == "settings:rename"
    command_aliases.show_panel.assert_awaited_once()
    callback.answer.assert_awaited_once()
