from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session, sessionmaker

from museums.db import (
    CityRow,
    MuseumRow,
    get_engine,
    get_session,
    init_db,
    upsert_city,
    upsert_museum,
)

_URL = "sqlite:///:memory:"


@pytest.fixture()
def session() -> Generator[Session, None, None]:
    engine = get_engine(_URL)
    factory = sessionmaker(engine, expire_on_commit=False)
    s = factory()
    try:
        yield s
        s.commit()
    finally:
        s.close()


# V1: museum row has name/city/country/visitors_annual >= 0
def test_museum_row_fields(session: Session) -> None:
    upsert_museum(session, "Louvre", "Paris", "France", 9_000_000)
    session.flush()
    from sqlalchemy import select

    row = session.execute(select(MuseumRow)).scalar_one()
    assert row.name == "Louvre"
    assert row.city == "Paris"
    assert row.country == "France"
    assert row.visitors_annual == 9_000_000
    assert row.visitors_annual >= 0


# V2: city row has name/country/population >= 0
def test_city_row_fields(session: Session) -> None:
    upsert_city(session, "Paris", "France", 2_000_000)
    session.flush()
    from sqlalchemy import select

    row = session.execute(select(CityRow)).scalar_one()
    assert row.name == "Paris"
    assert row.country == "France"
    assert row.population == 2_000_000
    assert row.population >= 0


# V7: rollback discards uncommitted writes
def test_transaction_rollback(session: Session) -> None:
    upsert_museum(session, "Temp Museum", "City", "Country", 100)
    session.flush()
    session.rollback()
    from sqlalchemy import select

    count = session.execute(select(MuseumRow)).all()
    assert len(count) == 0


# V15: get_session closes transaction after request completes
def test_get_session_closes() -> None:
    init_db(_URL)
    gen = get_session()
    s = next(gen)
    assert isinstance(s, Session)
    upsert_museum(s, "Temp", "City", "Country", 1)
    assert s.in_transaction()
    try:
        next(gen)
    except StopIteration:
        pass
    assert not s.in_transaction()


# V16: upsert_museum is idempotent by natural key
def test_upsert_museum_idempotent(session: Session) -> None:
    upsert_museum(session, "Louvre", "Paris", "France", 9_000_000)
    session.flush()
    upsert_museum(session, "Louvre", "Paris", "France", 9_500_000)
    session.flush()
    from sqlalchemy import select

    rows = session.execute(select(MuseumRow)).scalars().all()
    assert len(rows) == 1
    assert rows[0].visitors_annual == 9_500_000


# V16: upsert_city is idempotent by natural key
def test_upsert_city_idempotent(session: Session) -> None:
    upsert_city(session, "Paris", "France", 2_000_000)
    session.flush()
    upsert_city(session, "Paris", "France", 2_100_000)
    session.flush()
    from sqlalchemy import select

    rows = session.execute(select(CityRow)).scalars().all()
    assert len(rows) == 1
    assert rows[0].population == 2_100_000
