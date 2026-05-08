import logging

import pytest
from pytest_httpx import HTTPXMock

from museums.enricher import CityRecord, fetch_city_populations

_MOCK_RESPONSE = {
    "results": {
        "bindings": [
            {
                "name": {"value": "Paris"},
                "countryLabel": {"value": "France"},
                "population": {"value": "2161000"},
            },
            {
                "name": {"value": "London"},
                "countryLabel": {"value": "United Kingdom"},
                "population": {"value": "8982000"},
            },
        ]
    }
}


# V4, V5, V6: Wikidata queried via httpx; call is mocked
def test_fetch_returns_city_records(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json=_MOCK_RESPONSE)
    records = fetch_city_populations(["Paris", "London"])
    assert len(records) == 2
    assert all(isinstance(r, CityRecord) for r in records)


# V2: all records have non-empty name/country and population >= 0
def test_city_records_valid(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json=_MOCK_RESPONSE)
    for r in fetch_city_populations(["Paris", "London"]):
        assert r.name
        assert r.country
        assert r.population >= 0


# V6: empty input returns immediately without HTTP call
def test_empty_input_skips_http() -> None:
    result = fetch_city_populations([])
    assert result == []


# V20: city absent from Wikidata results logs a warning
def test_missing_city_logged(httpx_mock: HTTPXMock, caplog: pytest.LogCaptureFixture) -> None:
    httpx_mock.add_response(json=_MOCK_RESPONSE)
    with caplog.at_level(logging.WARNING, logger="museums.enricher"):
        fetch_city_populations(["Paris", "UnknownCity"])
    assert any("UnknownCity" in r.message for r in caplog.records)


# B19: binding with missing countryLabel is skipped + warned, not stored as empty string
def test_missing_country_skipped(httpx_mock: HTTPXMock, caplog: pytest.LogCaptureFixture) -> None:
    response = {
        "results": {
            "bindings": [
                {"name": {"value": "NoCountryCity"}, "population": {"value": "1000000"}},
            ]
        }
    }
    httpx_mock.add_response(json=response)
    with caplog.at_level(logging.WARNING, logger="museums.enricher"):
        records = fetch_city_populations(["NoCountryCity"])
    assert records == []
    assert any("NoCountryCity" in r.message for r in caplog.records)
