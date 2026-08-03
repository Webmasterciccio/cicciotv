"""Client HTTP minimale per le API di TMDB (The Movie Database)."""
from typing import Any

import httpx
from fastapi import HTTPException

from . import config

BASE_URL = "https://api.themoviedb.org/3"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w342"
BACKDROP_BASE_URL = "https://image.tmdb.org/t/p/w780"
STILL_BASE_URL = "https://image.tmdb.org/t/p/w300"      # miniature episodi
PROFILE_BASE_URL = "https://image.tmdb.org/t/p/w185"     # foto del cast
LOGO_BASE_URL = "https://image.tmdb.org/t/p/w92"         # loghi network/provider
PROVIDER_LOGO_BASE_URL = LOGO_BASE_URL

# Ordine e categorie dei servizi restituiti da TMDB in watch/providers.
_PROVIDER_KINDS = ("flatrate", "free", "ads", "rent", "buy")


def _img(base: str, path: str | None) -> str | None:
    return f"{base}{path}" if path else None


def _require_api_key() -> str:
    if not config.TMDB_API_KEY:
        raise HTTPException(
            status_code=500,
            detail=(
                "TMDB_API_KEY non configurata. Crea un file .env "
                "(vedi .env.example) con la tua chiave TMDB."
            ),
        )
    return config.TMDB_API_KEY


def _get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    api_key = _require_api_key()
    try:
        response = httpx.get(
            f"{BASE_URL}{path}",
            params={**params, "api_key": api_key, "language": config.TMDB_LANGUAGE},
            timeout=10.0,
        )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Impossibile contattare TMDB: {exc}") from exc

    if response.status_code == 401:
        raise HTTPException(status_code=502, detail="TMDB_API_KEY non valida.")
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Risorsa non trovata su TMDB.")
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502, detail=f"Errore TMDB ({response.status_code}): {response.text}"
        )
    return response.json()


def _poster_url(poster_path: str | None) -> str | None:
    return f"{POSTER_BASE_URL}{poster_path}" if poster_path else None


def _media_path(media_type: str) -> str:
    """Segmento di percorso TMDB per il tipo di media."""
    return "movie" if media_type == "movie" else "tv"


def search_tv(query: str) -> list[dict[str, Any]]:
    """Cerca serie TV per titolo. Restituisce risultati semplificati."""
    data = _get("/search/tv", {"query": query})
    return [
        {
            "tmdb_id": item["id"],
            "media_type": "tv",
            "title": item.get("name"),
            "overview": item.get("overview"),
            "first_air_date": item.get("first_air_date") or None,
            "poster_url": _poster_url(item.get("poster_path")),
        }
        for item in data.get("results", [])
    ]


def search_movie(query: str) -> list[dict[str, Any]]:
    """Cerca film per titolo. Restituisce risultati semplificati."""
    data = _get("/search/movie", {"query": query})
    return [
        {
            "tmdb_id": item["id"],
            "media_type": "movie",
            "title": item.get("title"),
            "overview": item.get("overview"),
            "first_air_date": item.get("release_date") or None,
            "poster_url": _poster_url(item.get("poster_path")),
        }
        for item in data.get("results", [])
    ]


def search(query: str, media_type: str = "tv") -> list[dict[str, Any]]:
    return search_movie(query) if media_type == "movie" else search_tv(query)


def get_tv_details(tmdb_id: int) -> dict[str, Any]:
    """Recupera i dettagli completi di una serie da TMDB."""
    data = _get(f"/tv/{tmdb_id}", {})
    return {
        "tmdb_id": data["id"],
        "title": data.get("name"),
        "overview": data.get("overview"),
        "total_seasons": data.get("number_of_seasons"),
        "poster_url": _poster_url(data.get("poster_path")),
        "genres": [g["name"] for g in data.get("genres", []) if g.get("name")],
    }


def get_movie_details(tmdb_id: int) -> dict[str, Any]:
    """Recupera i dettagli essenziali di un film da TMDB (per l'importazione)."""
    data = _get(f"/movie/{tmdb_id}", {})
    return {
        "tmdb_id": data["id"],
        "title": data.get("title"),
        "overview": data.get("overview"),
        "runtime": data.get("runtime") or None,
        "poster_url": _poster_url(data.get("poster_path")),
        "genres": [g["name"] for g in data.get("genres", []) if g.get("name")],
    }


def get_season_episodes(tmdb_id: int, season_number: int) -> list[dict[str, Any]]:
    """Recupera l'elenco degli episodi di una stagione. Stagioni inesistenti (es. speciali mancanti) vengono ignorate."""
    try:
        data = _get(f"/tv/{tmdb_id}/season/{season_number}", {})
    except HTTPException as exc:
        if exc.status_code == 404:
            return []
        raise
    return [
        {
            "season_number": season_number,
            "episode_number": ep["episode_number"],
            "name": ep.get("name"),
            "overview": ep.get("overview") or None,
            "still_url": _img(STILL_BASE_URL, ep.get("still_path")),
            "air_date": ep.get("air_date") or None,
            "vote_average": ep.get("vote_average") or None,
            "runtime": ep.get("runtime"),
        }
        for ep in data.get("episodes", [])
    ]


def get_tv_extended(tmdb_id: int) -> dict[str, Any]:
    """Recupera tutte le informazioni disponibili di una serie da TMDB
    (generi, trama, valutazioni, network, cast, ecc.)."""
    try:
        data = _get(f"/tv/{tmdb_id}", {"append_to_response": "credits"})
    except HTTPException as exc:
        if exc.status_code == 404:
            return {}
        raise

    credits = data.get("credits", {})
    return {
        "tmdb_id": data.get("id"),
        "title": data.get("name"),
        "original_title": data.get("original_name"),
        "tagline": data.get("tagline") or None,
        "overview": data.get("overview") or None,
        "poster_url": _img(POSTER_BASE_URL, data.get("poster_path")),
        "backdrop_url": _img(BACKDROP_BASE_URL, data.get("backdrop_path")),
        "genres": [g["name"] for g in data.get("genres", []) if g.get("name")],
        "vote_average": data.get("vote_average") or None,
        "vote_count": data.get("vote_count") or None,
        "first_air_date": data.get("first_air_date") or None,
        "last_air_date": data.get("last_air_date") or None,
        "status": data.get("status") or None,
        "in_production": data.get("in_production"),
        "number_of_seasons": data.get("number_of_seasons"),
        "number_of_episodes": data.get("number_of_episodes"),
        "episode_run_time": (data.get("episode_run_time") or [None])[0],
        "homepage": data.get("homepage") or None,
        "original_language": data.get("original_language") or None,
        "networks": [
            {"name": n.get("name"), "logo_url": _img(LOGO_BASE_URL, n.get("logo_path"))}
            for n in data.get("networks", [])
        ],
        "created_by": [c["name"] for c in data.get("created_by", []) if c.get("name")],
        "cast": [
            {
                "name": p.get("name"),
                "character": p.get("character") or None,
                "profile_url": _img(PROFILE_BASE_URL, p.get("profile_path")),
            }
            for p in credits.get("cast", [])[:15]
        ],
        "seasons": [
            {
                "season_number": s.get("season_number"),
                "name": s.get("name"),
                "overview": s.get("overview") or None,
                "poster_url": _img(POSTER_BASE_URL, s.get("poster_path")),
                "episode_count": s.get("episode_count"),
                "air_date": s.get("air_date") or None,
                "vote_average": s.get("vote_average") or None,
            }
            for s in data.get("seasons", [])
        ],
    }


def get_movie_extended(tmdb_id: int) -> dict[str, Any]:
    """Tutte le informazioni disponibili di un film da TMDB, nello stesso
    formato di get_tv_extended (cosi' il frontend usa un'unica scheda)."""
    try:
        data = _get(f"/movie/{tmdb_id}", {"append_to_response": "credits"})
    except HTTPException as exc:
        if exc.status_code == 404:
            return {}
        raise

    credits = data.get("credits", {})
    directors = [c["name"] for c in credits.get("crew", []) if c.get("job") == "Director" and c.get("name")]
    return {
        "tmdb_id": data.get("id"),
        "title": data.get("title"),
        "original_title": data.get("original_title"),
        "tagline": data.get("tagline") or None,
        "overview": data.get("overview") or None,
        "poster_url": _img(POSTER_BASE_URL, data.get("poster_path")),
        "backdrop_url": _img(BACKDROP_BASE_URL, data.get("backdrop_path")),
        "genres": [g["name"] for g in data.get("genres", []) if g.get("name")],
        "vote_average": data.get("vote_average") or None,
        "vote_count": data.get("vote_count") or None,
        "first_air_date": data.get("release_date") or None,
        "last_air_date": None,
        "status": data.get("status") or None,
        "in_production": None,
        "number_of_seasons": None,
        "number_of_episodes": None,
        "episode_run_time": data.get("runtime") or None,
        "homepage": data.get("homepage") or None,
        "original_language": data.get("original_language") or None,
        "networks": [
            {"name": n.get("name"), "logo_url": _img(LOGO_BASE_URL, n.get("logo_path"))}
            for n in data.get("production_companies", [])
        ],
        "created_by": directors,
        "cast": [
            {
                "name": p.get("name"),
                "character": p.get("character") or None,
                "profile_url": _img(PROFILE_BASE_URL, p.get("profile_path")),
            }
            for p in credits.get("cast", [])[:15]
        ],
        "seasons": [],
    }


def _norm_item(item: dict[str, Any], media_type: str) -> dict[str, Any]:
    """Normalizza un risultato film/serie in un formato comune."""
    is_movie = media_type == "movie"
    return {
        "tmdb_id": item["id"],
        "title": item.get("title") if is_movie else item.get("name"),
        "poster_url": _img(POSTER_BASE_URL, item.get("poster_path")),
        "vote_average": item.get("vote_average") or None,
        "first_air_date": (item.get("release_date") if is_movie else item.get("first_air_date"))
        or None,
        "overview": item.get("overview") or None,
        "original_language": item.get("original_language") or None,
    }


# Il genere "Animazione" (id 16) e' gestito dalla sezione Anime (Jikan): lo
# escludiamo da serie/film TMDB, sia dai generi selezionabili sia dai consigli.
ANIMATION_GENRE_ID = 16


def get_genres(media_type: str = "tv") -> list[dict[str, Any]]:
    """Elenco dei generi (di serie o film) su TMDB, senza 'Animazione'."""
    data = _get(f"/genre/{_media_path(media_type)}/list", {})
    return [
        {"id": g["id"], "name": g.get("name")}
        for g in data.get("genres", [])
        if g["id"] != ANIMATION_GENRE_ID
    ]


# Mappa i valori di ordinamento "amichevoli" ai parametri sort_by di TMDB.
_SORT_MAP = {
    "popularity": "popularity.desc",
    "rating": "vote_average.desc",
    "recent": "first_air_date.desc",  # per i film viene tradotto in primary_release_date
}


def discover_by_genres(
    genre_ids: list[int],
    media_type: str = "tv",
    page: int = 1,
    sort: str = "popularity",
    min_rating: float | None = None,
    year_from: int | None = None,
    lang: str | None = None,
) -> list[dict[str, Any]]:
    """Trova serie o film per uno o piu' generi, con ordinamento e filtri."""
    if not genre_ids:
        return []
    is_movie = media_type == "movie"
    sort_by = _SORT_MAP.get(sort, "popularity.desc")
    if is_movie and sort_by == "first_air_date.desc":
        sort_by = "primary_release_date.desc"

    params: dict[str, Any] = {
        "with_genres": ",".join(str(g) for g in genre_ids),
        # L'animazione e' coperta dalla sezione Anime: la escludiamo dai consigli
        # di serie/film cosi' i titoli animati non compaiono qui.
        "without_genres": str(ANIMATION_GENRE_ID),
        "sort_by": sort_by,
        # Con l'ordinamento per voto serve una soglia alta di voti per evitare
        # titoli oscuri con 10/10 su pochissime valutazioni.
        "vote_count.gte": 200 if sort == "rating" else 50,
        "include_adult": "false",
        "page": page,
    }
    if min_rating is not None:
        params["vote_average.gte"] = min_rating
    if year_from is not None:
        key = "primary_release_date.gte" if is_movie else "first_air_date.gte"
        params[key] = f"{year_from}-01-01"
    if lang:
        params["with_original_language"] = lang

    data = _get(f"/discover/{_media_path(media_type)}", params)
    return [_norm_item(item, media_type) for item in data.get("results", [])]


def get_recommendations(tmdb_id: int, media_type: str = "tv") -> list[dict[str, Any]]:
    """Media consigliati/simili. Usa 'recommendations' e, se vuoto, ripiega su 'similar'."""
    base = _media_path(media_type)
    results: list[dict[str, Any]] = []
    for path in ("recommendations", "similar"):
        try:
            data = _get(f"/{base}/{tmdb_id}/{path}", {})
        except HTTPException as exc:
            if exc.status_code == 404:
                continue
            raise
        results = data.get("results", [])
        if results:
            break
    return [_norm_item(item, media_type) for item in results]


def get_watch_providers(tmdb_id: int, media_type: str = "tv") -> dict[str, Any]:
    """Servizi su cui e' possibile guardare il media nella regione configurata (config.TMDB_REGION)."""
    try:
        data = _get(f"/{_media_path(media_type)}/{tmdb_id}/watch/providers", {})
    except HTTPException as exc:
        if exc.status_code == 404:
            return {"link": None, "providers": {}}
        raise

    region = data.get("results", {}).get(config.TMDB_REGION, {})
    providers: dict[str, list[dict[str, Any]]] = {}
    for kind in _PROVIDER_KINDS:
        items = region.get(kind)
        if not items:
            continue
        providers[kind] = [
            {
                "name": p.get("provider_name"),
                "logo_url": (
                    f"{PROVIDER_LOGO_BASE_URL}{p['logo_path']}" if p.get("logo_path") else None
                ),
            }
            for p in sorted(items, key=lambda x: x.get("display_priority", 999))
        ]
    return {"link": region.get("link"), "providers": providers}
