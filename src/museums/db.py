import logging

logger = logging.getLogger(__name__)


def get_engine(database_url: str) -> object: ...
