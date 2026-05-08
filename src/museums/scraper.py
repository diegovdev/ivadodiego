import io
import logging
import re

import httpx
import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_URL = "https://en.wikipedia.org/api/rest_v1/page/html/List_of_most_visited_museums"
_HEADERS = {"User-Agent": "museums-api/0.1.0 (https://github.com/diegovdev/ivadodiego)"}
_REQUIRED_COLS = {"Name", "Visitors", "City", "Country"}


class MuseumRecord(BaseModel):
    name: str
    city: str
    country: str
    visitors_annual: int = Field(ge=0)


def fetch_museums() -> list[MuseumRecord]:
    response = httpx.get(_URL, headers=_HEADERS, follow_redirects=True)
    response.raise_for_status()
    return _parse(response.text)


def _parse(html: str) -> list[MuseumRecord]:
    tables = pd.read_html(io.StringIO(html), flavor="html5lib")
    df = next(
        (t for t in tables if _REQUIRED_COLS.issubset({str(c) for c in t.columns})),
        None,
    )
    if df is None:
        raise ValueError("museum table not found in Wikipedia page")
    records: list[MuseumRecord] = []
    for _, row in df.iterrows():
        name = _clean(str(row["Name"]))
        city = _clean(str(row["City"]))
        country = _clean(str(row["Country"]))
        visitors = _parse_int(str(row["Visitors"]))
        if visitors is None:
            logger.warning("skipping %s — unparseable visitors: %r", name, row["Visitors"])
            continue
        records.append(
            MuseumRecord(name=name, city=city, country=country, visitors_annual=visitors)
        )
    logger.info("scraped %d museum records", len(records))
    return records


def _clean(value: str) -> str:
    return re.sub(r"\[.*?\]", "", value).strip()


def _parse_int(value: str) -> int | None:
    # format: "9,000,000 (2025) [1]" — take leading number only
    m = re.match(r"^[\d,]+", value.strip())
    if not m:
        return None
    return int(m.group().replace(",", ""))
