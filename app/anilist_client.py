"""Client per AniList (GraphQL): anime e manga.

Sostituisce Jikan/MyAnimeList come fonte primaria: nessuna chiave richiesta e
l'API si e' rivelata molto piu' stabile (Jikan dipende da MyAnimeList a monte,
spesso irraggiungibile). Stessa interfaccia pubblica di jikan_client.py, cosi'
il dispatcher (app/catalog.py) puo' scambiarli senza toccare il resto.
"""
import re
from typing import Any, Optional

from . import http_util

URL = "https://graphql.anilist.co"
SERVICE = "AniList"
# Elenco fisso dei generi AniList (GenreCollection): l'ordine determina gli id
# che esponiamo (interi, come richiesto dallo schema Genre). Va tenuto stabile:
# se AniList aggiunge generi, i nuovi vanno accodati, mai inseriti in mezzo.
_GENRES = (
    "Action", "Adventure", "Comedy", "Drama", "Ecchi", "Fantasy", "Hentai",
    "Horror", "Mahou Shoujo", "Mecha", "Music", "Mystery", "Psychological",
    "Romance", "Sci-Fi", "Slice of Life", "Sports", "Supernatural", "Thriller",
)
_GENRE_BY_ID = {i + 1: name for i, name in enumerate(_GENRES)}
_ID_BY_GENRE = {name: i + 1 for i, name in enumerate(_GENRES)}

_EPISODE_NUM_RE = re.compile(r"^Episode\s*(\d+)\s*-?\s*", re.IGNORECASE)


def _type_of(media_type: str) -> str:
    return "MANGA" if media_type == "manga" else "ANIME"


def _query(query: str, variables: dict) -> dict:
    data = http_util.post_json(
        URL,
        {"query": query, "variables": variables},
        service=SERVICE,
        min_interval=0.35,
        retries=2,
    )
    return data.get("data") or {}


def _title(m: dict) -> Optional[str]:
    t = m.get("title") or {}
    return t.get("english") or t.get("romaji") or t.get("native") or None


def _date(d: Optional[dict]) -> Optional[str]:
    if not d or not d.get("year"):
        return None
    return f"{d['year']:04d}-{(d.get('month') or 1):02d}-{(d.get('day') or 1):02d}"


def _score(m: dict) -> Optional[float]:
    s = m.get("averageScore")
    return round(s / 10, 1) if s else None


def _poster(m: dict) -> Optional[str]:
    return (m.get("coverImage") or {}).get("large")


def _normalize(m: dict, media_type: str) -> dict[str, Any]:
    return {
        "source": "anilist",
        "external_id": str(m.get("id")),
        "media_type": media_type,
        "title": _title(m),
        "poster_url": _poster(m),
        "overview": http_util.strip_html(m.get("description")),
        "date": _date(m.get("startDate")),
        "vote_average": _score(m),
        "authors": [],
        "genres": m.get("genres") or [],
        "progress_total": m.get("episodes") if media_type == "anime" else m.get("chapters"),
    }


_SEARCH_QUERY = """
query ($q: String, $type: MediaType) {
  Page(perPage: 20) {
    media(search: $q, type: $type, sort: SEARCH_MATCH) {
      id title { romaji english native } coverImage { large } description(asHtml: false)
      startDate { year month day } averageScore genres episodes chapters
    }
  }
}
"""


def search(query: str, media_type: str = "anime") -> list[dict[str, Any]]:
    """Cerca anime o manga per titolo."""
    data = _query(_SEARCH_QUERY, {"q": query, "type": _type_of(media_type)})
    items = ((data.get("Page") or {}).get("media")) or []
    return [_normalize(m, media_type) for m in items]


_DETAILS_QUERY = """
query ($id: Int) {
  Media(id: $id) {
    id title { romaji english native } description(asHtml: false)
    coverImage { large } genres averageScore startDate { year month day }
    endDate { year month day } status episodes chapters volumes duration
    homepage: siteUrl countryOfOrigin
    studios(isMain: true) { nodes { name } }
    staff(perPage: 8) { edges { role node { name { full } } } }
    characters(perPage: 15, sort: [ROLE, RELEVANCE]) {
      edges { role node { name { full } image { medium } } }
    }
  }
}
"""


def _is_author_role(role: str) -> bool:
    role = (role or "").lower()
    return "story" in role or "art" in role


def get_details(media_type: str, external_id: str) -> dict[str, Any]:
    """Dettagli estesi di un anime/manga, nel formato comune MediaDetails."""
    data = _query(_DETAILS_QUERY, {"id": int(external_id)})
    m = data.get("Media")
    if not m:
        return {}
    is_manga = media_type == "manga"
    staff_edges = (m.get("staff") or {}).get("edges") or []
    authors = [
        e["node"]["name"]["full"]
        for e in staff_edges
        if _is_author_role(e.get("role", "")) and e.get("node", {}).get("name", {}).get("full")
    ] or [
        e["node"]["name"]["full"]
        for e in staff_edges[:2]
        if e.get("node", {}).get("name", {}).get("full")
    ]
    studios = [s["name"] for s in (m.get("studios") or {}).get("nodes", []) if s.get("name")]
    cast = [
        {
            "name": e["node"]["name"]["full"],
            "character": None,
            "profile_url": (e["node"].get("image") or {}).get("medium"),
        }
        for e in ((m.get("characters") or {}).get("edges") or [])
        if e.get("node", {}).get("name", {}).get("full")
    ]
    return {
        "source": "anilist",
        "external_id": str(m.get("id")),
        "media_type": media_type,
        "tmdb_id": None,
        "title": _title(m),
        "original_title": (m.get("title") or {}).get("native"),
        "tagline": None,
        "overview": http_util.strip_html(m.get("description")),
        "poster_url": _poster(m),
        "backdrop_url": None,
        "genres": m.get("genres") or [],
        "vote_average": _score(m),
        "vote_count": None,
        "first_air_date": _date(m.get("startDate")),
        "last_air_date": _date(m.get("endDate")),
        "status": m.get("status") or None,
        "in_production": m.get("status") == "RELEASING",
        "number_of_seasons": None,
        "number_of_episodes": m.get("episodes") if not is_manga else None,
        "episode_run_time": m.get("duration") if not is_manga else None,
        "homepage": m.get("homepage") or None,
        "original_language": "ja" if m.get("countryOfOrigin") == "JP" else None,
        "authors": authors if is_manga else [],
        "studio": studios[0] if (studios and not is_manga) else None,
        "publisher": None,
        "chapters": m.get("chapters") if is_manga else None,
        "volumes": m.get("volumes") if is_manga else None,
        "page_count": None,
        "networks": [],
        "created_by": authors if is_manga else studios,
        "cast": cast,
        "seasons": [],
    }


_EPISODES_QUERY = """
query ($id: Int) {
  Media(id: $id) {
    episodes
    streamingEpisodes { title thumbnail }
  }
}
"""


def get_episodes(external_id: str) -> list[dict[str, Any]]:
    """Elenco episodi di un anime (per la tabella Episode).

    AniList non ha un endpoint per-episodio ufficiale: usa 'streamingEpisodes'
    (titoli/miniature dai partner streaming) quando disponibile. Se assente ma
    il numero totale di episodi e' noto, genera comunque le righe (senza
    titolo/miniatura) cosi' il tracciamento visti/non-visti resta possibile."""
    data = _query(_EPISODES_QUERY, {"id": int(external_id)})
    m = data.get("Media") or {}
    streaming = m.get("streamingEpisodes") or []
    if streaming:
        episodes = []
        for i, ep in enumerate(streaming, start=1):
            title = ep.get("title") or ""
            match = _EPISODE_NUM_RE.match(title)
            number = int(match.group(1)) if match else i
            name = _EPISODE_NUM_RE.sub("", title).strip() or None
            episodes.append(
                {
                    "season_number": 1,
                    "episode_number": number,
                    "name": name,
                    "overview": None,
                    "still_url": ep.get("thumbnail") or None,
                    "air_date": None,
                    "vote_average": None,
                    "runtime": None,
                }
            )
        episodes.sort(key=lambda e: e["episode_number"])
        return episodes

    total = m.get("episodes")
    if total:
        return [
            {
                "season_number": 1,
                "episode_number": i,
                "name": None,
                "overview": None,
                "still_url": None,
                "air_date": None,
                "vote_average": None,
                "runtime": None,
            }
            for i in range(1, total + 1)
        ]
    return []


_RECS_QUERY = """
query ($id: Int, $type: MediaType) {
  Media(id: $id) {
    recommendations(perPage: 12, sort: RATING_DESC) {
      nodes {
        mediaRecommendation {
          id title { romaji english } coverImage { large } averageScore
          startDate { year } description(asHtml: false)
        }
      }
    }
  }
}
"""


def get_recommendations(media_type: str, external_id: str) -> list[dict[str, Any]]:
    """Anime/manga consigliati a partire da un titolo."""
    data = _query(_RECS_QUERY, {"id": int(external_id), "type": _type_of(media_type)})
    nodes = ((data.get("Media") or {}).get("recommendations") or {}).get("nodes") or []
    results = []
    for n in nodes:
        rec = n.get("mediaRecommendation")
        if not rec or not rec.get("id"):
            continue
        results.append(
            {
                "source": "anilist",
                "external_id": str(rec["id"]),
                "media_type": media_type,
                "title": _title(rec),
                "poster_url": _poster(rec),
                "vote_average": _score(rec),
                "first_air_date": _date(rec.get("startDate")),
                "overview": http_util.strip_html(rec.get("description")),
                "original_language": "ja",
                "reason": None,
            }
        )
    return results


def get_genres(media_type: str = "anime") -> list[dict[str, Any]]:
    """Elenco fisso dei generi AniList, con id stabili assegnati da noi."""
    return [{"id": gid, "name": name} for gid, name in _GENRE_BY_ID.items()]


_DISCOVER_QUERY = """
query ($genres: [String], $type: MediaType, $page: Int) {
  Page(page: $page, perPage: 24) {
    media(genre_in: $genres, type: $type, sort: POPULARITY_DESC) {
      id title { romaji english } coverImage { large } description(asHtml: false)
      startDate { year month day } averageScore genres episodes chapters
    }
  }
}
"""


def discover_by_genres(
    genre_ids: list[int], media_type: str = "anime", page: int = 1, **_ignored: Any
) -> list[dict[str, Any]]:
    """Titoli popolari per uno o piu' generi (riempimento dei consigli)."""
    names = [_GENRE_BY_ID[g] for g in genre_ids if g in _GENRE_BY_ID]
    if not names:
        return []
    data = _query(_DISCOVER_QUERY, {"genres": names, "type": _type_of(media_type), "page": page})
    items = ((data.get("Page") or {}).get("media")) or []
    return [_normalize(m, media_type) for m in items]


_POPULAR_QUERY = """
query ($type: MediaType, $page: Int) {
  Page(page: $page, perPage: 24) {
    media(type: $type, sort: POPULARITY_DESC) {
      id title { romaji english } coverImage { large } description(asHtml: false)
      startDate { year month day } averageScore genres episodes chapters
    }
  }
}
"""


def get_popular(media_type: str = "anime", page: int = 1) -> list[dict[str, Any]]:
    """Titoli piu' popolari (fallback quando non ci sono semi/generi)."""
    data = _query(_POPULAR_QUERY, {"type": _type_of(media_type), "page": page})
    items = ((data.get("Page") or {}).get("media")) or []
    return [_normalize(m, media_type) for m in items]
