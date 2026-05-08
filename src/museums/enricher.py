"""Enrich city names with country and population via Wikidata SPARQL."""

import logging
from typing import NotRequired, TypedDict

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_SPARQL_URL = "https://query.wikidata.org/sparql"
_HEADERS = {
    "User-Agent": "museums-api/0.1.0 (https://github.com/diegovdev/ivadodiego)",
    "Accept": "application/sparql-results+json",
}


# B18: TypedDict over dict[str, Any] — typo-safe at type-check time, no runtime cost.
# countryLabel NotRequired: wikibase:label SERVICE omits it when no English label (B19).
class _SparqlValue(TypedDict):
    value: str


class _Binding(TypedDict):
    name: _SparqlValue
    population: _SparqlValue
    countryLabel: NotRequired[_SparqlValue]


class _SparqlResults(TypedDict):
    bindings: list[_Binding]


class _SparqlResponse(TypedDict):
    results: _SparqlResults


class CityRecord(BaseModel):
    """One enriched city: name, country, and non-negative population."""

    name: str
    country: str
    population: int = Field(ge=0)


def fetch_city_populations(city_names: list[str]) -> list[CityRecord]:
    """Look up populations for the given English city names via Wikidata SPARQL.

    Issues one request per city so no single query times out on Wikidata's label index.
    Names with no Wikidata match (V20 exact-string limitation) or no English country
    label (B19) are dropped with a warning. Empty input returns [] without HTTP calls.

    Raises:
        httpx.HTTPStatusError: if the SPARQL endpoint returns a non-2xx response.
    """
    if not city_names:
        return []
    records: list[CityRecord] = []
    for name in city_names:
        record = _fetch_one(name)
        if record is None:
            logger.warning("no Wikidata match for city %r — V20 exact-string limitation", name)
        else:
            records.append(record)
    logger.info("enriched %d/%d cities", len(records), len(city_names))
    return records


def _sparql_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _build_query(name: str) -> str:
    # Scope to human settlements (Q486972) to avoid matching non-city entities
    # with the same label. Single-city query stays well within Wikidata's 60s timeout.
    return f"""
SELECT ?countryLabel (MAX(?pop) AS ?population) WHERE {{
  ?city rdfs:label {_sparql_str(name)}@en .
  ?city wdt:P31/wdt:P279* wd:Q486972 .
  ?city wdt:P1082 ?pop .
  ?city wdt:P17 ?country .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
}}
GROUP BY ?countryLabel
LIMIT 1
"""


def _fetch_one(name: str) -> CityRecord | None:
    response = httpx.get(
        _SPARQL_URL,
        params={"query": _build_query(name)},
        headers=_HEADERS,
        timeout=15.0,
    )
    response.raise_for_status()
    data: _SparqlResponse = response.json()
    bindings = data["results"]["bindings"]
    if not bindings:
        return None
    b = bindings[0]
    country_obj = b.get("countryLabel")
    if country_obj is None or not country_obj["value"]:
        logger.warning("skipping %r — missing countryLabel in Wikidata binding", name)
        return None
    return CityRecord(
        name=name,
        country=country_obj["value"],
        population=int(b["population"]["value"]),
    )
