import pytest

from museums import configure_logging


@pytest.fixture(autouse=True)
def _configure_logging() -> None:
    configure_logging()
