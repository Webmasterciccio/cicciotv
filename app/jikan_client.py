"""Client per Jikan (API non ufficiale di MyAnimeList): anime e manga.

Nessuna chiave richiesta. Jikan e' rate-limited (circa 3 richieste/secondo), quindi
usiamo cache TTL e un piccolo throttle tramite http_util.
"""
from typing import Any, Optional

from fastapi import HTTPException

from . import http_util

BASE_URL = "https://api.jikan.moe/v4"
SERVICE = "Jikan"
# Intervallo minimo tra due chiamate: resta abbondantemente sotto i limiti.
_MIN_INTERVAL = 0.5


def _type_path(media_type: str) -> str:
    """Segmento di percorso Jikan per il tipo ('anime' o 'manga')."""
    return "manga" if media_type == "manga" else "anime"


def _get(path: str, params: Optional[dict] = None, *, not_found_ok: bool = False) -> Optional[dict]:
    return http_util.get_json(
        f"{BASE_URL}{path}",
        params=params,
        service=SERVICE,
        min_interval=_MIN_INTERVAL,
        not_found_ok=not_found_ok,
        retries=3,  # MyAnimeList a monte e' spesso intermittente: piu' tentativi
    )


def _poster(item: dict) -> Optional[str]:
    images = item.get("images") or {}
    jpg = images.get("jpg") or {}
    return jpg.get("large_image_url") or jpg.get("image_url") or None


def _title(item: dict) -> Optional[str]:
    # Jikan non ha titoli in italiano: preferiamo l'inglese, poi il romaji.
    return item.get("title_english") or item.get("title") or None


def _date(item: dict, media_type: str) -> Optional[str]:
    block = item.get("published") if media_type == "manga" else item.get("aired")
    prop = (block or {}).get("prop") or {}
    frm = prop.get("from") or {}
    y, m, d = frm.get("year"), frm.get("month"), frm.get("day")
    if not y:
        # Ripiego sulla stringa ISO se presente.
        iso = (block or {}).get("from")
        return iso[:10] if iso else None
    return f"{y:04d}-{(m or 1):02d}-{(d or 1):02d}"


def _genres(item: dict) -> list[str]:
    return [g.get("name") for g in (item.get("genres") or []) if g.get("name")]


def _progress_total(item: dict, media_type: str) -> Optional[int]:
    if media_type == "manga":
        return item.get("chapters") or None
    return item.get("episodes") or None


def _normalize(item: dict, media_type: str) -> dict[str, Any]:
    """Item Jikan -> formato normalizzato comune (ricerca/consigli)."""
    return {
        "source": "jikan",
        "external_id": str(item.get("mal_id")),
        "media_type": media_type,
        "title": _title(item),
        "poster_url": _poster(item),
        "overview": item.get("synopsis") or None,
        "date": _date(item, media_type),
        "vote_average": item.get("score") or None,
        "authors": [a.get("name") for a in (item.get("authors") or []) if a.get("name")],
        "genres": _genres(item),
        "progress_total": _progress_total(item, media_type),
    }


def search(query: str, media_type: str = "anime") -> list[dict[str, Any]]:
    """Cerca anime o manga per titolo."""
    # Parametri minimi: Jikan va in timeout (504) quando la ricerca testuale e'
    # combinata con order_by/filtri pesanti. La rilevanza di default basta.
    data = _get(
        f"/{_type_path(media_type)}",
        {"q": query, "limit": 20, "sfw": "true"},
    )
    return [_normalize(item, media_type) for item in (data or {}).get("data", [])]


def get_details(media_type: str, external_id: str) -> dict[str, Any]:
    """Dettagli estesi di un anime/manga, nel formato comune MediaDetails."""
    data = _get(f"/{_type_path(media_type)}/{external_id}", not_found_ok=True)
    if not data or "data" not in data:
        return {}
    item = data["data"]
    is_manga = media_type == "manga"
    authors = [a.get("name") for a in (item.get("authors") or []) if a.get("name")]
    studios = [s.get("name") for s in (item.get("studios") or []) if s.get("name")]
    return {
        "source": "jikan",
        "external_id": str(item.get("mal_id")),
        "media_type": media_type,
        "tmdb_id": None,
        "title": _title(item),
        "original_title": item.get("title_japanese") or item.get("title"),
        "tagline": None,
        "overview": item.get("synopsis") or None,
        "poster_url": _poster(item),
        "backdrop_url": None,
        "genres": _genres(item),
        "vote_average": item.get("score") or None,
        "vote_count": item.get("scored_by") or None,
        "first_air_date": _date(item, media_type),
        "last_air_date": ((item.get("published") if is_manga else item.get("aired")) or {}).get("to"),
        "status": item.get("status") or None,
        "in_production": item.get("airing") if not is_manga else item.get("publishing"),
        "number_of_seasons": None,
        "number_of_episodes": item.get("episodes") if not is_manga else None,
        "episode_run_time": None,
        "homepage": item.get("url") or None,
        "original_language": "ja",
        "authors": authors,
        "studio": ", ".join(studios) or None,
        "publisher": ", ".join(
            s.get("name") for s in (item.get("serializations") or []) if s.get("name")
        )
        or None,
        "chapters": item.get("chapters") if is_manga else None,
        "volumes": item.get("volumes") if is_manga else None,
        "page_count": None,
        "networks": [],
        "created_by": authors or studios,
        "cast": [],
        "seasons": [],
    }


def get_episodes(external_id: str) -> list[dict[str, Any]]:
    """Elenco episodi di un anime (per la tabella Episode). Solo anime."""
    episodes: list[dict[str, Any]] = []
    page = 1
    index = 0
    while True:
        data = _get(f"/anime/{external_id}/episodes", {"page": page}, not_found_ok=True)
        if not data:
            break
        for ep in data.get("data", []):
            index += 1
            episodes.append(
                {
                    "season_number": 1,
                    "episode_number": ep.get("mal_id") or index,
                    "name": ep.get("title") or ep.get("title_romanji"),
                    "overview": None,
                    "still_url": None,
                    "air_date": (ep.get("aired") or "")[:10] or None,
                    "vote_average": ep.get("score") or None,
                    "runtime": None,
                }
            )
        pagination = data.get("pagination") or {}
        if not pagination.get("has_next_page") or page >= 25:  # limite di sicurezza
            break
        page += 1
    return episodes


def get_recommendations(media_type: str, external_id: str) -> list[dict[str, Any]]:
    """Anime/manga consigliati a partire da un titolo."""
    data = _get(
        f"/{_type_path(media_type)}/{external_id}/recommendations", not_found_ok=True
    )
    results: list[dict[str, Any]] = []
    for rec in (data or {}).get("data", []):
        entry = rec.get("entry") or {}
        if not entry.get("mal_id"):
            continue
        results.append(
            {
                "source": "jikan",
                "external_id": str(entry.get("mal_id")),
                "media_type": media_type,
                "title": entry.get("title"),
                "poster_url": _poster(entry),
                "vote_average": None,
                "first_air_date": None,
                "overview": None,
                "original_language": "ja",
                "reason": None,
            }
        )
    return results


def get_genres(media_type: str = "anime") -> list[dict[str, Any]]:
    """Elenco dei generi (per anime o manga)."""
    data = _get(f"/genres/{_type_path(media_type)}", not_found_ok=True)
    return [
        {"id": g.get("mal_id"), "name": g.get("name")}
        for g in (data or {}).get("data", [])
        if g.get("mal_id")
    ]


def discover_by_genres(
    genre_ids: list[int], media_type: str = "anime", page: int = 1, **_ignored: Any
) -> list[dict[str, Any]]:
    """Titoli popolari per uno o piu' generi (riempimento dei consigli)."""
    if not genre_ids:
        return []
    data = _get(
        f"/{_type_path(media_type)}",
        {
            "genres": ",".join(str(g) for g in genre_ids),
            "order_by": "popularity",
            "sfw": "true",
            "page": page,
            "limit": 24,
        },
        not_found_ok=True,
    )
    return [_normalize(item, media_type) for item in (data or {}).get("data", [])]


def get_popular(media_type: str = "anime", page: int = 1) -> list[dict[str, Any]]:
    """Titoli piu' popolari (fallback quando non ci sono semi/generi)."""
    data = _get(
        f"/top/{_type_path(media_type)}",
        {"page": page, "limit": 24},
        not_found_ok=True,
    )
    return [_normalize(item, media_type) for item in (data or {}).get("data", [])]
