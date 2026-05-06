import logging

logger = logging.getLogger(__name__)


def fetch_city_populations(city_names: list[str]) -> list[dict[str, object]]: ...
