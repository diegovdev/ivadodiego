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
    name: str
    country: str
    population: int = Field(ge=0)


def fetch_city_populations(city_names: list[str]) -> list[CityRecord]:
    if not city_names:
        return []
    response = httpx.get(
        _SPARQL_URL,
        params={"query": _build_query(city_names)},
        headers=_HEADERS,
        timeout=15.0,
    )
    response.raise_for_status()
    return _parse_results(response.json(), city_names)


def _sparql_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _build_query(city_names: list[str]) -> str:
    values = " ".join(_sparql_str(n) for n in city_names)
    return f"""
SELECT DISTINCT ?name ?countryLabel (MAX(?pop) AS ?population) WHERE {{
  VALUES ?name {{ {values} }}
  ?city rdfs:label ?nameLabel .
  FILTER(LANG(?nameLabel) = "en" && STR(?nameLabel) = ?name)
  ?city wdt:P1082 ?pop .
  ?city wdt:P17 ?country .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
}}
GROUP BY ?name ?countryLabel
"""


def _parse_results(data: _SparqlResponse, city_names: list[str]) -> list[CityRecord]:
    found: dict[str, CityRecord] = {}
    for b in data["results"]["bindings"]:
        name = b["name"]["value"]
        country_obj = b.get("countryLabel")
        if country_obj is None or not country_obj["value"]:
            logger.warning("skipping %r — missing countryLabel in Wikidata binding", name)
            continue
        population = int(b["population"]["value"])
        found[name] = CityRecord(name=name, country=country_obj["value"], population=population)
    missing = set(city_names) - set(found)
    for m in sorted(missing):
        logger.warning("no Wikidata match for city %r — V20 exact-string limitation", m)
    logger.info("enriched %d/%d cities", len(found), len(city_names))
    return list(found.values())
