import logging
from collections.abc import Generator
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import CheckConstraint, String, UniqueConstraint, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

logger = logging.getLogger(__name__)

_session_factory: sessionmaker[Session] | None = None


class Base(DeclarativeBase):
    pass


class MuseumRow(Base):
    __tablename__ = "museums"
    __table_args__ = (
        UniqueConstraint("name", "city", "country", name="uq_museum_natural_key"),
        CheckConstraint("visitors_annual >= 0", name="ck_museum_visitors_nonneg"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    city: Mapped[str] = mapped_column(String, nullable=False)
    country: Mapped[str] = mapped_column(String, nullable=False)
    visitors_annual: Mapped[int] = mapped_column(nullable=False)


class CityRow(Base):
    __tablename__ = "cities"
    __table_args__ = (
        UniqueConstraint("name", "country", name="uq_city_natural_key"),
        CheckConstraint("population >= 0", name="ck_city_population_nonneg"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    country: Mapped[str] = mapped_column(String, nullable=False)
    population: Mapped[int] = mapped_column(nullable=False)


def get_engine(database_url: str) -> Engine:
    return create_engine(database_url)


def init_db(database_url: str) -> None:
    global _session_factory
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    _session_factory = sessionmaker(engine, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    if _session_factory is None:
        raise RuntimeError("DB not initialised — call init_db() first")
    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


SessionDep = Annotated[Session, Depends(get_session)]


def upsert_museum(
    session: Session, name: str, city: str, country: str, visitors_annual: int
) -> MuseumRow:
    row = session.execute(
        select(MuseumRow).where(
            MuseumRow.name == name,
            MuseumRow.city == city,
            MuseumRow.country == country,
        )
    ).scalar_one_or_none()
    if row is None:
        row = MuseumRow(name=name, city=city, country=country, visitors_annual=visitors_annual)
        session.add(row)
    else:
        row.visitors_annual = visitors_annual
    return row


def upsert_city(session: Session, name: str, country: str, population: int) -> CityRow:
    row = session.execute(
        select(CityRow).where(CityRow.name == name, CityRow.country == country)
    ).scalar_one_or_none()
    if row is None:
        row = CityRow(name=name, country=country, population=population)
        session.add(row)
    else:
        row.population = population
    return row


def get_all_museums(session: Session) -> list[MuseumRow]:
    return session.execute(select(MuseumRow)).scalars().all()


def get_museum_by_id(session: Session, museum_id: int) -> MuseumRow | None:
    return session.execute(select(MuseumRow).where(MuseumRow.id == museum_id)).scalar_one_or_none()


def get_all_cities(session: Session) -> list[CityRow]:
    return session.execute(select(CityRow)).scalars().all()


def get_training_rows(session: Session) -> list[Any]:
    # Join on city+country composite — city name alone is ambiguous across countries
    return session.execute(
        select(MuseumRow.visitors_annual, CityRow.population).join(
            CityRow,
            (MuseumRow.city == CityRow.name) & (MuseumRow.country == CityRow.country),
        )
    ).all()
