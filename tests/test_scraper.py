from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from museums.scraper import MuseumRecord, _parse, fetch_museums

_FIXTURE = Path(__file__).parent / "fixtures" / "wikipedia_museums.html"


@pytest.fixture()
def fixture_html() -> str:
    return _FIXTURE.read_text(encoding="utf-8")


# V3, V39: fixture file present at repo-relative path
def test_fixture_file_exists() -> None:
    assert _FIXTURE.exists()
    assert _FIXTURE.stat().st_size > 10_000


# V19: parse uses pandas.read_html, returns non-empty list[MuseumRecord]
def test_parse_returns_museum_records(fixture_html: str) -> None:
    records = _parse(fixture_html)
    assert len(records) > 0
    assert all(isinstance(r, MuseumRecord) for r in records)


# V1: all records have required non-empty fields and visitors_annual >= 0
def test_all_records_valid(fixture_html: str) -> None:
    for r in _parse(fixture_html):
        assert r.name
        assert r.city
        assert r.country
        assert r.visitors_annual >= 0


# V5, V6: fetch_museums uses httpx; HTTP call is mocked
def test_fetch_museums_uses_httpx_mocked(httpx_mock: HTTPXMock, fixture_html: str) -> None:
    httpx_mock.add_response(text=fixture_html)
    records = fetch_museums()
    assert len(records) > 0
    assert all(isinstance(r, MuseumRecord) for r in records)
