import logging

from sqlalchemy import Engine

logger = logging.getLogger(__name__)


def get_engine(database_url: str) -> Engine: ...
