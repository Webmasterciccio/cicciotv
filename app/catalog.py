"""Dispatcher multi-sorgente: instrada ogni tipo di media al client giusto e
normalizza le risposte in un formato comune ("card") usato da ricerca, consigli
e importazione.

Sorgenti:
- tv, movie -> TMDB (tmdb_client). L'anime NON e' una sezione separata: e'
  incorporato in "tv". Se TMDB non trova il titolo cercato, la ricerca ripiega
  su AniList (stesso media_type "tv", source "anilist").
- manga     -> AniList (anilist_client)
- book      -> Google Books (googlebooks_client)
- comic     -> Comic Vine (comicvine_client)

Le sorgenti "anilist"/"jikan" parlano di "anime" internamente: quando servono
per un titolo "tv" (fallback, o righe preesistenti dell'ex sezione anime) si
traduce il tipo prima di chiamare il client e lo si riporta a "tv" nel
risultato, cosi' il resto dell'app vede sempre e solo "tv".
"""
from typing import Any, Optional

from fastapi import HTTPException

from . import anilist_client, comicvine_client, googlebooks_client, jikan_client, schemas, tmdb_client

# Tipi che tracciano singole "unita'" (episodi/numeri) nella tabella Episode.
UNIT_TYPES = {"tv", "comic"}
# Tipi di media gestiti dal catalogo (l'anime confluisce in "tv").
MEDIA_TYPES = ("tv", "movie", "manga", "book", "comic")

# Sorgenti "stile anime" (episodi in lista piatta, no stagioni), usate anche
# per media_type "tv" quando il titolo non e' su TMDB.
_ANIME_LIKE_SOURCES = {"anilist", "jikan"}


def source_for(media_type: str) -> str:
    return {
        "tv": "tmdb",
        "movie": "tmdb",
        "manga": "anilist",
        "book": "googlebooks",
        "comic": "comicvine",
    }.get(media_type, "tmdb")


def _client_type(media_type: str, source: str) -> str:
    """Tipo da passare ai client Jikan/AniList: 'tv' diventa 'anime' quando la
    sorgente e' anime-like; 'manga' resta 'manga'."""
    if media_type == "tv" and source in _ANIME_LIKE_SOURCES:
        return "anime"
    return media_type


def _card(item: dict, media_type: str) -> dict[str, Any]:
    """Normalizza un risultato (ricerca/consiglio) nel formato comune."""
    return {
        "source": item.get("source"),
        "external_id": item.get("external_id"),
        "media_type": media_type,
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
    if media_type == "movie":
        return [_tmdb_card(it, media_type) for it in tmdb_client.search(query, media_type)]
    if media_type == "tv":
        results = [_tmdb_card(it, "tv") for it in tmdb_client.search(query, "tv")]
        if not results:
            # Titolo non trovato su TMDB (tipico di anime recenti/di nicchia):
            # ripiega su AniList, restituendo comunque media_type "tv".
            results = [_card(it, "tv") for it in anilist_client.search(query, "anime")]
        return results
    if media_type == "manga":
        return [_card(it, "manga") for it in anilist_client.search(query, "manga")]
    if media_type == "book":
        return [_card(it, "book") for it in googlebooks_client.search(query, media_type)]
    if media_type == "comic":
        return [_card(it, "comic") for it in comicvine_client.search(query, media_type)]
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
    if source == "anilist":
        details = anilist_client.get_details(_client_type(media_type, source), external_id)
        if details:
            details["media_type"] = media_type
        return details
    if source == "jikan":
        details = jikan_client.get_details(_client_type(media_type, source), external_id)
        if details:
            details["media_type"] = media_type
        return details
    if source == "googlebooks":
        return googlebooks_client.get_details(media_type, external_id)
    if source == "comicvine":
        return comicvine_client.get_details(media_type, external_id)
    return {}


# --- Unita' (episodi/numeri) ---

def has_units(media_type: str) -> bool:
    return media_type in UNIT_TYPES


def get_units(media_type: str, source: str, external_id: str) -> list[dict[str, Any]]:
    """Episodi (serie TV non-TMDB, ex sezione anime) o numeri (fumetti). Le
    serie TV da TMDB usano il percorso dedicato (stagioni) nel router; qui
    gestiamo tv via AniList/Jikan e i fumetti via Comic Vine."""
    if media_type == "tv" and source == "anilist":
        return anilist_client.get_episodes(external_id)
    if media_type == "tv" and source == "jikan":
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
    if source == "anilist":
        recs = anilist_client.get_recommendations(_client_type(media_type, source), external_id)
        return [_card(it, media_type) for it in recs]
    if source == "jikan":
        recs = jikan_client.get_recommendations(_client_type(media_type, source), external_id)
        return [_card(it, media_type) for it in recs]
    if source == "googlebooks":
        recs = googlebooks_client.get_recommendations(media_type, external_id)
        return [_card(it, media_type) for it in recs]
    if source == "comicvine":
        recs = comicvine_client.get_recommendations(media_type, external_id)
        return [_card(it, media_type) for it in recs]
    return []


def get_watch_providers(media_type: str, source: str, external_id: str) -> dict[str, Any]:
    """Servizi 'dove vederla' (solo serie/film TMDB); vuoto per gli altri tipi."""
    if source == "tmdb" and external_id and external_id.isdigit():
        return tmdb_client.get_watch_providers(int(external_id), media_type)
    return {"link": None, "providers": {}}


def get_genres(media_type: str) -> list[dict[str, Any]]:
    if media_type in ("tv", "movie"):
        return tmdb_client.get_genres(media_type)
    if media_type == "manga":
        return anilist_client.get_genres("manga")
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
    if media_type == "manga":
        items = anilist_client.discover_by_genres(genre_ids, "manga", page)
        return [_card(it, "manga") for it in items]
    return []


def get_popular(media_type: str, page: int = 1) -> list[dict[str, Any]]:
    if media_type in ("tv", "movie"):
        return [_tmdb_card(it, media_type) for it in tmdb_client.discover_by_genres(
            [], media_type, page=page)] or []
    if media_type == "manga":
        return [_card(it, "manga") for it in anilist_client.get_popular("manga", page)]
    if media_type == "book":
        return [_card(it, "book") for it in googlebooks_client.get_popular(media_type, page)]
    if media_type == "comic":
        return [_card(it, "comic") for it in comicvine_client.get_popular(media_type, page)]
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
    elif media_type == "comic":
        progress_total = details.get("number_of_episodes")
    else:
        # "tv" (anime non su TMDB): il progresso e' tracciato episodio per
        # episodio nella tabella Episode, non come contatore numerico.
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
    units = get_units(media_type, source, external_id) if has_units(media_type) else []
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
