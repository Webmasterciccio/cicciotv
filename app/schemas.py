"""Schemi Pydantic per validazione input e serializzazione output."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import Status


class SeriesBase(BaseModel):
    """Campi comuni, tutti opzionali tranne dove indicato."""

    title: str = Field(..., min_length=1, description="Titolo della serie")
    status: Status = Field(default=Status.da_vedere, description="Stato di visione")
    rating: Optional[int] = Field(default=None, ge=1, le=10, description="Voto da 1 a 10")
    notes: Optional[str] = None

    total_seasons: Optional[int] = Field(default=None, ge=0)
    current_season: Optional[int] = Field(default=None, ge=0)
    current_episode: Optional[int] = Field(default=None, ge=0)

    tmdb_id: Optional[int] = None
    poster_url: Optional[str] = None


class SeriesCreate(SeriesBase):
    """Dati necessari per creare una serie."""


class SeriesUpdate(BaseModel):
    """Tutti i campi opzionali: si aggiorna solo cio' che viene passato."""

    title: Optional[str] = Field(default=None, min_length=1)
    status: Optional[Status] = None
    rating: Optional[int] = Field(default=None, ge=1, le=10)
    notes: Optional[str] = None

    total_seasons: Optional[int] = Field(default=None, ge=0)
    current_season: Optional[int] = Field(default=None, ge=0)
    current_episode: Optional[int] = Field(default=None, ge=0)

    tmdb_id: Optional[int] = None
    poster_url: Optional[str] = None


class SeriesRead(SeriesBase):
    """Rappresentazione completa restituita dall'API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class TmdbSearchResult(BaseModel):
    """Un risultato di ricerca da TMDB (non ancora salvato in libreria)."""

    tmdb_id: int
    title: Optional[str] = None
    overview: Optional[str] = None
    first_air_date: Optional[str] = None
    poster_url: Optional[str] = None


class EpisodeRead(BaseModel):
    """Un episodio con il suo stato di visione."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    season_number: int
    episode_number: int
    name: Optional[str] = None
    watched: bool
    watched_at: Optional[datetime] = None


class EpisodeWatchedUpdate(BaseModel):
    """Payload per segnare un episodio (o una stagione) come visto/non visto."""

    watched: bool
