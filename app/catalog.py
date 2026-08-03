"""Dispatcher multi-sorgente: instrada ogni tipo di media al client giusto e
normalizza le risposte in un formato comune ("card") usato da ricerca, consigli
e importazione.

Sorgenti:
- tv, movie   -> TMDB (tmdb_client)
- anime, manga-> Jikan (jikan_client)
- book        -> Google Books (googlebooks_client)
- comic       -> Comic Vine (comicvine_client)
"""
from typing import Any, Optional

from fastapi import HTTPException

from . import comicvine_client, googlebooks_client, jikan_client, schemas, tmdb_client

# Tipi che tracciano singole "unita'" (episodi/numeri) nella tabella Episode.
UNIT_TYPES = {"tv", "anime", "comic"}
# Etichette leggibili delle sorgenti (per messaggi/preferenze).
MEDIA_TYPES = ("tv", "movie", "anime", "manga", "book", "comic")


def source_for(media_type: str) -> str:
    return {
        "tv": "tmdb",
        "movie": "tmdb",
        "anime": "jikan",
        "manga": "jikan",
        "book": "googlebooks",
        "comic": "comicvine",
    }.get(media_type, "tmdb")


def _card(item: dict, media_type: Optional[str] = None) -> dict[str, Any]:
    """Normalizza un risultato (ricerca/consiglio) nel formato comune."""
    return {
        "source": item.get("source"),
        "external_id": item.get("external_id"),
        "media_type": item.get("media_type") or media_type,
        "title": item.get("title"),
        "poster_url": item.get("poster_url"),
        "overview": item.get("overview"),
        "vote_average": item.get("vote_average"),
        "first_air_date": item.get("first_air_date") or item.get("date"),
        "original_language": item.get("original_language"),
        "authors": item.get("authors") or [],
        "genres": item.get("genres") or [],
        "reason": item.get("reason"),
    }


# --- TMDB: adattatori (le funzioni tmdb_client usano id interi e chiavi proprie) ---

def _tmdb_card(item: dict, media_type: str) -> dict[str, Any]:
    return {
        "source": "tmdb",
        "external_id": str(item.get("tmdb_id")),
        "media_type": media_type,
        "title": item.get("title"),
        "poster_url": item.get("poster_url"),
        "overview": item.get("overview"),
        "vote_average": item.get("vote_average"),
        "first_air_date": item.get("first_air_date"),
        "original_language": item.get("original_language"),
        "authors": [],
        "genres": [],
        "reason": item.get("reason"),
    }


# --- Ricerca ---

def search(query: str, media_type: str) -> list[dict[str, Any]]:
    if media_type in ("tv", "movie"):
        return [_tmdb_card(it, media_type) for it in tmdb_client.search(query, media_type)]
    if media_type in ("anime", "manga"):
        return [_card(it) for it in jikan_client.search(query, media_type)]
    if media_type == "book":
        return [_card(it) for it in googlebooks_client.search(query, media_type)]
    if media_type == "comic":
        return [_card(it) for it in comicvine_client.search(query, media_type)]
    raise HTTPException(status_code=400, detail=f"Tipo non valido: {media_type}")


# --- Dettagli estesi (per la pagina di dettaglio) ---

_DETAILS_DEFAULTS = {
    "authors": [],
    "studio": None,
    "publisher": None,
    "chapters": None,
    "volumes": None,
    "page_count": None,
}


def get_details(media_type: str, source: str, external_id: str) -> dict[str, Any]:
    if source == "tmdb":
        if not external_id or not external_id.isdigit():
            return {}
        tmdb_id = int(external_id)
        details = (
            tmdb_client.get_movie_extended(tmdb_id)
            if media_type == "movie"
            else tmdb_client.get_tv_extended(tmdb_id)
        )
        if not details:
            return {}
        # Completa con i campi non-TMDB attesi da MediaDetails.
        merged = {**_DETAILS_DEFAULTS, "source": "tmdb", "external_id": external_id, **details}
        merged["media_type"] = media_type
        return merged
    if source == "jikan":
        return jikan_client.get_details(media_type, external_id)
    if source == "googlebooks":
        return googlebooks_client.get_details(media_type, external_id)
    if source == "comicvine":
        return comicvine_client.get_details(media_type, external_id)
    return {}


# --- Unita' (episodi/numeri) ---

def has_units(media_type: str) -> bool:
    return media_type in UNIT_TYPES


def get_units(media_type: str, external_id: str) -> list[dict[str, Any]]:
    """Episodi (anime) o numeri (fumetti). Le serie TV usano il percorso TMDB
    dedicato (stagioni) nel router; qui gestiamo anime e fumetti."""
    if media_type == "anime":
        return jikan_client.get_episodes(external_id)
    if media_type == "comic":
        return comicvine_client.get_issues(external_id)
    return []


# --- Consigli / discover / popolari (formato card) ---

def get_recommendations(media_type: str, source: str, external_id: str) -> list[dict[str, Any]]:
    if source == "tmdb":
        if not external_id or not external_id.isdigit():
            return []
        recs = tmdb_client.get_recommendations(int(external_id), media_type)
        return [_tmdb_card(it, media_type) for it in recs]
    if source == "jikan":
        return [_card(it) for it in jikan_client.get_recommendations(media_type, external_id)]
    if source == "googlebooks":
        return [_card(it) for it in googlebooks_client.get_recommendations(media_type, external_id)]
    if source == "comicvine":
        return [_card(it) for it in comicvine_client.get_recommendations(media_type, external_id)]
    return []


def get_genres(media_type: str) -> list[dict[str, Any]]:
    if media_type in ("tv", "movie"):
        return tmdb_client.get_genres(media_type)
    if media_type in ("anime", "manga"):
        return jikan_client.get_genres(media_type)
    return []  # libri/fumetti: nessuna preferenza di genere


def discover(
    media_type: str,
    genre_ids: list[int],
    page: int = 1,
    sort: str = "popularity",
    min_rating: Optional[float] = None,
    year_from: Optional[int] = None,
    lang: Optional[str] = None,
) -> list[dict[str, Any]]:
    if media_type in ("tv", "movie"):
        items = tmdb_client.discover_by_genres(
            genre_ids, media_type, page=page, sort=sort,
            min_rating=min_rating, year_from=year_from, lang=lang,
        )
        return [_tmdb_card(it, media_type) for it in items]
    if media_type in ("anime", "manga"):
        return [_card(it) for it in jikan_client.discover_by_genres(genre_ids, media_type, page)]
    return []


def get_popular(media_type: str, page: int = 1) -> list[dict[str, Any]]:
    if media_type in ("tv", "movie"):
        return [_tmdb_card(it, media_type) for it in tmdb_client.discover_by_genres(
            [], media_type, page=page)] or []
    if media_type in ("anime", "manga"):
        return [_card(it) for it in jikan_client.get_popular(media_type, page)]
    if media_type == "book":
        return [_card(it) for it in googlebooks_client.get_popular(media_type, page)]
    if media_type == "comic":
        return [_card(it) for it in comicvine_client.get_popular(media_type, page)]
    return []


# --- Importazione ---

def build_import(media_type: str, source: str, external_id: str) -> tuple[schemas.SeriesCreate, list[dict]]:
    """Costruisce lo SeriesCreate per l'import e restituisce le unita' da
    sincronizzare (episodi/numeri) se il tipo le prevede."""
    if source == "tmdb":
        return _build_tmdb_import(media_type, external_id)

    details = get_details(media_type, source, external_id)
    if not details:
        raise HTTPException(status_code=404, detail="Titolo non trovato sulla sorgente")

    genres = ",".join(details.get("genres") or []) or None
    if media_type == "manga":
        progress_total = details.get("chapters")
    elif media_type == "book":
        progress_total = details.get("page_count")
    elif media_type == "anime":
        progress_total = details.get("number_of_episodes")
    elif media_type == "comic":
        progress_total = details.get("number_of_episodes")
    else:
        progress_total = None

    payload = schemas.SeriesCreate(
        title=details.get("title") or "(senza titolo)",
        media_type=media_type,
        source=source,
        external_id=str(external_id),
        poster_url=details.get("poster_url"),
        genres=genres,
        progress_total=progress_total,
    )
    units = get_units(media_type, external_id) if has_units(media_type) else []
    return payload, units


def _build_tmdb_import(media_type: str, external_id: str) -> tuple[schemas.SeriesCreate, list[dict]]:
    tmdb_id = int(external_id)
    if media_type == "movie":
        details = tmdb_client.get_movie_details(tmdb_id)
        payload = schemas.SeriesCreate(
            title=details["title"],
            media_type="movie",
            source="tmdb",
            external_id=str(tmdb_id),
            tmdb_id=tmdb_id,
            runtime=details["runtime"],
            poster_url=details["poster_url"],
            genres=",".join(details.get("genres") or []) or None,
        )
        return payload, []

    details = tmdb_client.get_tv_details(tmdb_id)
    payload = schemas.SeriesCreate(
        title=details["title"],
        media_type="tv",
        source="tmdb",
        external_id=str(tmdb_id),
        tmdb_id=tmdb_id,
        total_seasons=details["total_seasons"],
        poster_url=details["poster_url"],
        genres=",".join(details.get("genres") or []) or None,
    )
    # Le serie TV scaricano gli episodi per stagione (percorso TMDB dedicato).
    units: list[dict] = []
    if details.get("total_seasons"):
        for season_number in range(1, details["total_seasons"] + 1):
            units.extend(tmdb_client.get_season_episodes(tmdb_id, season_number))
    return payload, units
