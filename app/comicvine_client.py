"""Client per Comic Vine (fumetti occidentali).

Richiede una API key gratuita (config.COMICVINE_API_KEY) e uno User-Agent non
vuoto (Comic Vine blocca gli user-agent generici). E' rate-limited
(~200 richieste/risorsa/ora): ci affidiamo alla cache TTL di http_util.
"""
from typing import Any, Optional

from fastapi import HTTPException

from . import config, http_util
from .http_util import strip_html as _strip_html

BASE_URL = "https://comicvine.gamespot.com/api"
SERVICE = "Comic Vine"
_HEADERS = {"User-Agent": "CiccioTV/1.0"}
# Prefisso del tipo-risorsa "volume" negli id Comic Vine (una serie a fumetti).
_VOLUME_PREFIX = "4050-"


def _require_key() -> str:
    if not config.COMICVINE_API_KEY:
        raise HTTPException(
            status_code=500,
            detail=(
                "COMICVINE_API_KEY non configurata. Registrati su comicvine.gamespot.com "
                "e incolla la chiave da comicvine.gamespot.com/api/ nel file .env."
            ),
        )
    return config.COMICVINE_API_KEY


def _get(path: str, extra: dict, *, not_found_ok: bool = False) -> Optional[dict]:
    params = {"api_key": _require_key(), "format": "json", **extra}
    return http_util.get_json(
        f"{BASE_URL}{path}",
        params=params,
        headers=_HEADERS,
        service=SERVICE,
        min_interval=0.5,
        timeout=25.0,  # Comic Vine e' spesso lento, specie sull'elenco dei numeri
        not_found_ok=not_found_ok,
    )


def _poster(item: dict) -> Optional[str]:
    image = item.get("image") or {}
    return image.get("medium_url") or image.get("small_url") or image.get("original_url") or None


def _year(item: dict) -> Optional[str]:
    y = item.get("start_year")
    return str(y) if y else None


def _normalize(item: dict) -> dict[str, Any]:
    publisher = (item.get("publisher") or {}).get("name")
    return {
        "source": "comicvine",
        "external_id": str(item.get("id")),
        "media_type": "comic",
        "title": item.get("name"),
        "poster_url": _poster(item),
        "overview": _strip_html(item.get("deck")) or _strip_html(item.get("description")),
        "date": _year(item),
        "vote_average": None,
        "authors": [publisher] if publisher else [],
        "genres": [],
        "progress_total": item.get("count_of_issues") or None,
    }


def search(query: str, media_type: str = "comic") -> list[dict[str, Any]]:
    """Cerca serie a fumetti (volumi) per titolo."""
    data = _get(
        "/search/",
        {
            "query": query,
            "resources": "volume",
            "limit": 20,
            "field_list": "id,name,image,deck,start_year,publisher,count_of_issues",
        },
    )
    return [_normalize(v) for v in (data or {}).get("results", [])]


def get_details(media_type: str, external_id: str) -> dict[str, Any]:
    """Dettagli di un volume nel formato comune MediaDetails."""
    data = _get(f"/volume/{_VOLUME_PREFIX}{external_id}/", {}, not_found_ok=True)
    item = (data or {}).get("results")
    if not item:
        return {}
    publisher = (item.get("publisher") or {}).get("name")
    characters = [
        c.get("name") for c in (item.get("characters") or [])[:15] if c.get("name")
    ]
    return {
        "source": "comicvine",
        "external_id": str(item.get("id")),
        "media_type": "comic",
        "tmdb_id": None,
        "title": item.get("name"),
        "original_title": None,
        "tagline": _strip_html(item.get("deck")),
        "overview": _strip_html(item.get("description")),
        "poster_url": _poster(item),
        "backdrop_url": None,
        "genres": [],
        "vote_average": None,
        "vote_count": None,
        "first_air_date": _year(item),
        "last_air_date": None,
        "status": None,
        "in_production": None,
        "number_of_seasons": None,
        "number_of_episodes": item.get("count_of_issues") or None,
        "episode_run_time": None,
        "homepage": item.get("site_detail_url") or None,
        "original_language": "en",
        "authors": [publisher] if publisher else [],
        "studio": publisher,
        "publisher": publisher,
        "chapters": None,
        "volumes": None,
        "page_count": None,
        "networks": [],
        "created_by": [publisher] if publisher else [],
        # Riusiamo il "cast" per i personaggi principali della serie.
        "cast": [{"name": name, "character": None, "profile_url": None} for name in characters],
        "seasons": [],
    }


def get_issues(external_id: str) -> list[dict[str, Any]]:
    """Elenco dei numeri (issue) di un volume, per la tabella Episode."""
    data = _get(
        "/issues/",
        {
            "filter": f"volume:{external_id}",
            "sort": "cover_date:asc",
            "limit": 100,
            "field_list": "id,issue_number,name,cover_date,image",
        },
        not_found_ok=True,
    )
    issues: list[dict[str, Any]] = []
    for index, issue in enumerate((data or {}).get("results", []), start=1):
        number = issue.get("issue_number")
        label = f"#{number}" if number else f"#{index}"
        name = issue.get("name")
        image = issue.get("image") or {}
        issues.append(
            {
                "season_number": 1,
                "episode_number": index,
                "name": f"{label} {name}".strip() if name else label,
                "overview": None,
                "still_url": image.get("small_url") or image.get("thumb_url") or None,
                "air_date": issue.get("cover_date") or None,
                "vote_average": None,
                "runtime": None,
            }
        )
    return issues


def get_recommendations(media_type: str, external_id: str) -> list[dict[str, Any]]:
    """Comic Vine non ha consigli nativi: il riempimento usa i volumi popolari."""
    return []


def get_genres(media_type: str = "comic") -> list[dict[str, Any]]:
    return []


def get_popular(media_type: str = "comic", page: int = 1) -> list[dict[str, Any]]:
    """Volumi con piu' numeri (proxy di popolarita') come punto di partenza."""
    data = _get(
        "/volumes/",
        {
            "sort": "count_of_issues:desc",
            "limit": 24,
            "offset": (page - 1) * 24,
            "field_list": "id,name,image,deck,start_year,publisher,count_of_issues",
        },
        not_found_ok=True,
    )
    return [_normalize(v) for v in (data or {}).get("results", [])]
