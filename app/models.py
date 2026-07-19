"""Modelli del database (tabelle)."""
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from .database import Base


class Status(str, enum.Enum):
    """Stati possibili di una serie TV nella tua libreria."""

    da_vedere = "da_vedere"
    in_corso = "in_corso"
    vista = "vista"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Series(Base):
    __tablename__ = "series"

    id = Column(Integer, primary_key=True, index=True)

    # Dati principali
    title = Column(String, nullable=False, index=True)
    status = Column(Enum(Status), nullable=False, default=Status.da_vedere, index=True)
    rating = Column(Integer, nullable=True)  # voto 1-10
    notes = Column(Text, nullable=True)

    # Progresso di visione
    total_seasons = Column(Integer, nullable=True)
    current_season = Column(Integer, nullable=True)
    current_episode = Column(Integer, nullable=True)

    # Campi predisposti per l'integrazione futura con TMDB
    tmdb_id = Column(Integer, nullable=True, index=True)
    poster_url = Column(String, nullable=True)

    # Timestamp gestiti automaticamente
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
    started_at = Column(DateTime, nullable=True)   # quando hai iniziato a guardarla
    finished_at = Column(DateTime, nullable=True)  # quando l'hai finita


class Episode(Base):
    __tablename__ = "episodes"
    __table_args__ = (
        UniqueConstraint("series_id", "season_number", "episode_number", name="uq_episode_identity"),
    )

    id = Column(Integer, primary_key=True, index=True)
    series_id = Column(Integer, ForeignKey("series.id"), nullable=False, index=True)

    season_number = Column(Integer, nullable=False)
    episode_number = Column(Integer, nullable=False)
    name = Column(String, nullable=True)

    watched = Column(Boolean, nullable=False, default=False)
    watched_at = Column(DateTime, nullable=True)
