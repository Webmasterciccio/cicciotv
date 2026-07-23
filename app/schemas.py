"""Schemi Pydantic per validazione input e serializzazione output."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import Status


class SeriesBase(BaseModel):
    """Campi comuni, tutti opzionali tranne dove indicato."""

    title: str = Field(..., min_length=1, description="Titolo della serie")
    media_type: str = Field(default="tv", description="Tipo: 'tv' o 'movie'")
    status: Status = Field(default=Status.da_vedere, description="Stato di visione")
    rating: Optional[int] = Field(default=None, ge=1, le=10, description="Voto da 1 a 10")
    notes: Optional[str] = None
    runtime: Optional[int] = Field(default=None, ge=0, description="Durata in minuti (film)")
    watch_location: Optional[str] = Field(
        default=None, description="Dove l'ho visto (film): cinema, streaming, tv"
    )

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
    watch_location: Optional[str] = None
    genres: Optional[str] = None


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
    media_type: str = "tv"
    title: Optional[str] = None
    overview: Optional[str] = None
    first_air_date: Optional[str] = None
    poster_url: Optional[str] = None


class EpisodeRead(BaseModel):
    """Un episodio con il suo stato di visione e i dettagli da TMDB."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    season_number: int
    episode_number: int
    name: Optional[str] = None
    overview: Optional[str] = None
    still_url: Optional[str] = None
    air_date: Optional[str] = None
    vote_average: Optional[float] = None
    runtime: Optional[int] = None
    watched: bool
    watched_at: Optional[datetime] = None


class EpisodeWatchedUpdate(BaseModel):
    """Payload per segnare un episodio (o una stagione) come visto/non visto."""

    watched: bool


class WatchProvider(BaseModel):
    """Un servizio su cui e' disponibile la serie (nome + logo)."""

    name: Optional[str] = None
    logo_url: Optional[str] = None


class WatchProviders(BaseModel):
    """Servizi 'dove vederla' raggruppati per categoria (abbonamento, noleggio, ...)."""

    link: Optional[str] = None
    providers: dict[str, list[WatchProvider]] = Field(default_factory=dict)


class TmdbNetwork(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None


class TmdbCastMember(BaseModel):
    name: Optional[str] = None
    character: Optional[str] = None
    profile_url: Optional[str] = None


class TmdbSeason(BaseModel):
    season_number: Optional[int] = None
    name: Optional[str] = None
    overview: Optional[str] = None
    poster_url: Optional[str] = None
    episode_count: Optional[int] = None
    air_date: Optional[str] = None
    vote_average: Optional[float] = None


class TmdbDetails(BaseModel):
    """Tutte le informazioni disponibili di una serie su TMDB."""

    tmdb_id: Optional[int] = None
    title: Optional[str] = None
    original_title: Optional[str] = None
    tagline: Optional[str] = None
    overview: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    genres: list[str] = Field(default_factory=list)
    vote_average: Optional[float] = None
    vote_count: Optional[int] = None
    first_air_date: Optional[str] = None
    last_air_date: Optional[str] = None
    status: Optional[str] = None
    in_production: Optional[bool] = None
    number_of_seasons: Optional[int] = None
    number_of_episodes: Optional[int] = None
    episode_run_time: Optional[int] = None
    homepage: Optional[str] = None
    original_language: Optional[str] = None
    networks: list[TmdbNetwork] = Field(default_factory=list)
    created_by: list[str] = Field(default_factory=list)
    cast: list[TmdbCastMember] = Field(default_factory=list)
    seasons: list[TmdbSeason] = Field(default_factory=list)


class TmdbRecommendation(BaseModel):
    """Una serie consigliata/simile (non ancora in libreria)."""

    tmdb_id: int
    title: Optional[str] = None
    poster_url: Optional[str] = None
    vote_average: Optional[float] = None
    first_air_date: Optional[str] = None
    overview: Optional[str] = None
    original_language: Optional[str] = None
    reason: Optional[str] = None  # es. "Perché hai visto «Dark»"


class DismissRequest(BaseModel):
    """Payload per scartare un consiglio ('non mi interessa')."""

    tmdb_id: int
    media_type: str = Field(default="tv", pattern="^(tv|movie)$")


class Genre(BaseModel):
    id: int
    name: Optional[str] = None


class SettingsRead(BaseModel):
    """Preferenze dell'utente (generi preferiti separati per tipo)."""

    preferred_genres_tv: list[int] = Field(default_factory=list)
    preferred_genres_movie: list[int] = Field(default_factory=list)


class SettingsUpdate(BaseModel):
    """Aggiornamento parziale: si passa solo il tipo che si vuole modificare."""

    preferred_genres_tv: Optional[list[int]] = None
    preferred_genres_movie: Optional[list[int]] = None


class LoginRequest(BaseModel):
    """Payload di login: solo il PIN."""

    pin: str = Field(..., min_length=4, max_length=32)


class UserRead(BaseModel):
    """Un utente (senza dati sensibili: mai il PIN)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_admin: bool = False


class LoginResponse(BaseModel):
    token: str
    user: UserRead


class AuthStatus(BaseModel):
    """Stato dell'autenticazione: serve al frontend per capire se e' il primo avvio."""

    users_exist: bool


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=40)
    pin: str = Field(..., min_length=4, max_length=32)


class UserUpdate(BaseModel):
    """Aggiornamento parziale di un utente (nome e/o nuovo PIN)."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=40)
    pin: Optional[str] = Field(default=None, min_length=4, max_length=32)


class TopSeries(BaseModel):
    id: int
    title: str
    episodes_watched: int


class MonthCount(BaseModel):
    month: str  # formato "YYYY-MM"
    count: int


class InProgressSeries(BaseModel):
    id: int
    title: str
    watched: int
    total: int
    percent: int


class WeekdayCount(BaseModel):
    weekday: int  # 0 = lunedì ... 6 = domenica
    count: int


class MovieThisMonth(BaseModel):
    """Film visti questo mese, suddivisi per dove sono stati visti."""

    cinema: int = 0
    streaming: int = 0
    tv: int = 0
    total: int = 0


class MovieStats(BaseModel):
    """Statistiche relative ai film."""

    total: int
    to_watch: int
    watched: int
    minutes_watched: int
    average_rating: Optional[float] = None
    rated_count: int
    this_month: MovieThisMonth


class Stats(BaseModel):
    """Statistiche della libreria."""

    total_series: int
    to_watch: int
    watching: int
    completed: int
    total_episodes: int
    episodes_watched: int
    minutes_watched: int
    average_rating: Optional[float] = None
    rated_count: int
    top_series: list[TopSeries] = Field(default_factory=list)
    episodes_per_month: list[MonthCount] = Field(default_factory=list)
    in_progress: list[InProgressSeries] = Field(default_factory=list)
    movies: MovieStats
    watch_insights: list[str] = Field(default_factory=list)
    episodes_by_weekday: list[WeekdayCount] = Field(default_factory=list)
