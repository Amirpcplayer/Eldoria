import pytest

from utils.telegram_links import get_bot_deep_link


class FakeMe:
    def __init__(self, username):
        self.username = username


class FakeBot:
    def __init__(self, username):
        self.username = username

    async def get_me(self):
        return FakeMe(self.username)


@pytest.mark.asyncio
async def test_deep_link_uses_current_bot_username():
    url = await get_bot_deep_link(FakeBot("MyActualEldoriaBot"))
    assert url == "https://t.me/MyActualEldoriaBot"


@pytest.mark.asyncio
async def test_deep_link_supports_start_parameter():
    url = await get_bot_deep_link(FakeBot("MyActualEldoriaBot"), "restart")
    assert url == "https://t.me/MyActualEldoriaBot?start=restart"


@pytest.mark.asyncio
async def test_deep_link_encodes_start_parameter():
    url = await get_bot_deep_link(FakeBot("MyActualEldoriaBot"), "new player")
    assert url == "https://t.me/MyActualEldoriaBot?start=new%20player"


@pytest.mark.asyncio
async def test_deep_link_returns_none_without_username():
    assert await get_bot_deep_link(FakeBot(None)) is None
