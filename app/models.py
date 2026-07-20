"""Modelli del database (tabelle)."""
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
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

    # Tipo di media: "tv" (serie) o "movie" (film)
    media_type = Column(String, nullable=False, default="tv", index=True)

    # Dati principali
    title = Column(String, nullable=False, index=True)
    status = Column(Enum(Status), nullable=False, default=Status.da_vedere, index=True)
    rating = Column(Integer, nullable=True)  # voto 1-10
    notes = Column(Text, nullable=True)

    # Durata in minuti (usata soprattutto per i film)
    runtime = Column(Integer, nullable=True)

    # Dove l'ho visto (film): "cinema", "streaming" o "tv"
    watch_location = Column(String, nullable=True)

    # Progresso di visione
    total_seasons = Column(Integer, nullable=True)
    current_season = Column(Integer, nullable=True)
    current_episode = Column(Integer, nullable=True)

    # Campi predisposti per l'integrazione futura con TMDB
    tmdb_id = Column(Integer, nullable=True, index=True)
    poster_url = Column(String, nullable=True)
    genres = Column(Text, nullable=True)  # generi TMDB separati da virgola

    # Timestamp gestiti automaticamente
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
    started_at = Column(DateTime, nullable=True)   # quando hai iniziato a guardarla
    finished_at = Column(DateTime, nullable=True)  # quando l'hai finita


class Setting(Base):
    """Impostazioni dell'app in formato chiave-valore (es. generi preferiti)."""

    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)


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

    # Dettagli da TMDB (miniatura e informazioni episodio)
    overview = Column(Text, nullable=True)
    still_url = Column(String, nullable=True)   # miniatura dell'episodio
    air_date = Column(String, nullable=True)    # data di uscita (YYYY-MM-DD)
    vote_average = Column(Float, nullable=True)
    runtime = Column(Integer, nullable=True)    # durata in minuti

    watched = Column(Boolean, nullable=False, default=False)
    watched_at = Column(DateTime, nullable=True)
