import pytest


@pytest.fixture(scope="session", autouse=True)
def _pytest_session_marker():
    yield