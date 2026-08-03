"""Client per Google Books (libri).

La chiave e' opzionale (alza le quote): se presente in config viene aggiunta.
I voti di Google Books sono su scala 0-5: li normalizziamo su 0-10 (come TMDB e
Jikan) moltiplicando per 2, cosi' la UI mostra una scala coerente.
"""
from typing import Any, Optional

from . import config, http_util

BASE_URL = "https://www.googleapis.com/books/v1"
SERVICE = "Google Books"


def _params(extra: dict) -> dict:
    params = {"country": "IT", **extra}
    if config.GOOGLE_BOOKS_API_KEY:
        params["key"] = config.GOOGLE_BOOKS_API_KEY
    return params


def _get(path: str, extra: dict, *, not_found_ok: bool = False) -> Optional[dict]:
    return http_util.get_json(
        f"{BASE_URL}{path}",
        params=_params(extra),
        service=SERVICE,
        not_found_ok=not_found_ok,
    )


def _poster(info: dict) -> Optional[str]:
    links = info.get("imageLinks") or {}
    url = links.get("thumbnail") or links.get("smallThumbnail")
    # Google restituisce spesso URL http: forziamo https per il WebView/HTTPS.
    return url.replace("http://", "https://") if url else None


def _rating(info: dict) -> Optional[float]:
    r = info.get("averageRating")
    return round(r * 2, 1) if r else None


def _normalize(volume: dict) -> dict[str, Any]:
    info = volume.get("volumeInfo") or {}
    return {
        "source": "googlebooks",
        "external_id": volume.get("id"),
        "media_type": "book",
        "title": info.get("title"),
        "poster_url": _poster(info),
        "overview": info.get("description") or None,
        "date": info.get("publishedDate") or None,
        "vote_average": _rating(info),
        "authors": info.get("authors") or [],
        "genres": info.get("categories") or [],
        "progress_total": info.get("pageCount") or None,
    }


def search(query: str, media_type: str = "book") -> list[dict[str, Any]]:
    """Cerca libri per titolo/autore."""
    data = _get("/volumes", {"q": query, "maxResults": 20, "printType": "books"})
    return [_normalize(v) for v in (data or {}).get("items", [])]


def get_details(media_type: str, external_id: str) -> dict[str, Any]:
    """Dettagli di un libro nel formato comune MediaDetails."""
    volume = _get(f"/volumes/{external_id}", {}, not_found_ok=True)
    if not volume:
        return {}
    info = volume.get("volumeInfo") or {}
    return {
        "source": "googlebooks",
        "external_id": volume.get("id"),
        "media_type": "book",
        "tmdb_id": None,
        "title": info.get("title"),
        "original_title": info.get("subtitle"),
        "tagline": None,
        "overview": info.get("description") or None,
        "poster_url": _poster(info),
        "backdrop_url": None,
        "genres": info.get("categories") or [],
        "vote_average": _rating(info),
        "vote_count": info.get("ratingsCount") or None,
        "first_air_date": info.get("publishedDate") or None,
        "last_air_date": None,
        "status": None,
        "in_production": None,
        "number_of_seasons": None,
        "number_of_episodes": None,
        "episode_run_time": None,
        "homepage": info.get("infoLink") or info.get("canonicalVolumeLink") or None,
        "original_language": info.get("language") or None,
        "authors": info.get("authors") or [],
        "studio": None,
        "publisher": info.get("publisher") or None,
        "chapters": None,
        "volumes": None,
        "page_count": info.get("pageCount") or None,
        "networks": [],
        "created_by": info.get("authors") or [],
        "cast": [],
        "seasons": [],
    }


def get_recommendations(media_type: str, external_id: str) -> list[dict[str, Any]]:
    """Google Books non ha 'consigli' nativi: proponiamo altri libri dello stesso
    autore (o categoria), escludendo il libro di partenza."""
    volume = _get(f"/volumes/{external_id}", {}, not_found_ok=True)
    if not volume:
        return []
    info = volume.get("volumeInfo") or {}
    authors = info.get("authors") or []
    categories = info.get("categories") or []
    if authors:
        q = f'inauthor:"{authors[0]}"'
    elif categories:
        q = f'subject:"{categories[0]}"'
    else:
        return []
    data = _get("/volumes", {"q": q, "maxResults": 20, "printType": "books"})
    out: list[dict[str, Any]] = []
    for v in (data or {}).get("items", []):
        if v.get("id") == external_id:
            continue
        n = _normalize(v)
        out.append(
            {
                "source": "googlebooks",
                "external_id": n["external_id"],
                "media_type": "book",
                "title": n["title"],
                "poster_url": n["poster_url"],
                "vote_average": n["vote_average"],
                "first_air_date": n["date"],
                "overview": n["overview"],
                "original_language": None,
                "reason": None,
            }
        )
    return out


def get_genres(media_type: str = "book") -> list[dict[str, Any]]:
    """Google Books non espone un elenco di generi: nessuna preferenza di genere."""
    return []


def get_popular(media_type: str = "book", page: int = 1) -> list[dict[str, Any]]:
    """Libri di partenza quando non ci sono semi: bestseller/narrativa recenti."""
    start = (page - 1) * 20
    data = _get(
        "/volumes",
        {
            "q": "subject:fiction",
            "orderBy": "relevance",
            "maxResults": 20,
            "startIndex": start,
            "printType": "books",
        },
    )
    return [_normalize(v) for v in (data or {}).get("items", [])]
