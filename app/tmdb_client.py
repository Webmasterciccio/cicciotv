"""Client HTTP minimale per le API di TMDB (The Movie Database)."""
from typing import Any

import httpx
from fastapi import HTTPException

from . import config

BASE_URL = "https://api.themoviedb.org/3"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w342"


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


def search_tv(query: str) -> list[dict[str, Any]]:
    """Cerca serie TV per titolo. Restituisce risultati semplificati."""
    data = _get("/search/tv", {"query": query})
    return [
        {
            "tmdb_id": item["id"],
            "title": item.get("name"),
            "overview": item.get("overview"),
            "first_air_date": item.get("first_air_date") or None,
            "poster_url": _poster_url(item.get("poster_path")),
        }
        for item in data.get("results", [])
    ]


def get_tv_details(tmdb_id: int) -> dict[str, Any]:
    """Recupera i dettagli completi di una serie da TMDB."""
    data = _get(f"/tv/{tmdb_id}", {})
    return {
        "tmdb_id": data["id"],
        "title": data.get("name"),
        "overview": data.get("overview"),
        "total_seasons": data.get("number_of_seasons"),
        "poster_url": _poster_url(data.get("poster_path")),
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
        }
        for ep in data.get("episodes", [])
    ]
