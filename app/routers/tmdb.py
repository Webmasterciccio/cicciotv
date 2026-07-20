"""Endpoint per la ricerca e l'importazione di serie da TMDB."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud, schemas, tmdb_client
from ..database import get_db
from ..models import Status

router = APIRouter(prefix="/tmdb", tags=["tmdb"])


MediaType = Query(default="tv", pattern="^(tv|movie)$", description="Tipo: 'tv' o 'movie'")


@router.get("/search", response_model=list[schemas.TmdbSearchResult])
def search(query: str = Query(..., min_length=1), type: str = MediaType):
    """Cerca serie TV o film su TMDB per titolo."""
    return tmdb_client.search(query, media_type=type)


@router.get("/genres", response_model=list[schemas.Genre])
def genres(type: str = MediaType):
    """Elenco dei generi (di serie o film) per scegliere le preferenze."""
    return tmdb_client.get_genres(media_type=type)


@router.get("/suggestions", response_model=list[schemas.TmdbRecommendation])
def suggestions(
    limit: int = Query(default=20, ge=1, le=40),
    type: str = MediaType,
    db: Session = Depends(get_db),
):
    """Consigli sul prossimo titolo da guardare, in base ai generi preferiti
    (per tipo) e ai titoli non ancora in libreria."""
    preferred = crud.get_preferred_genres(db, media_type=type)
    if not preferred:
        return []

    already = crud.get_library_tmdb_ids(db, media_type=type)
    picked: list[dict] = []
    seen: set[int] = set()
    # Scorre qualche pagina di risultati finche' non raggiunge il numero voluto.
    for page in range(1, 6):
        for item in tmdb_client.discover_by_genres(preferred, media_type=type, page=page):
            tid = item["tmdb_id"]
            if tid in already or tid in seen:
                continue
            seen.add(tid)
            picked.append(item)
            if len(picked) >= limit:
                return picked
    return picked


@router.post(
    "/import/{tmdb_id}",
    response_model=schemas.SeriesRead,
    status_code=status.HTTP_201_CREATED,
)
def import_series(
    tmdb_id: int,
    series_status: Status = Query(default=Status.da_vedere, alias="status"),
    type: str = MediaType,
    db: Session = Depends(get_db),
):
    """Importa una serie o un film da TMDB nella libreria locale."""
    existing = crud.get_series_by_tmdb_id(db, tmdb_id, media_type=type)
    if existing is not None:
        label = "Film" if type == "movie" else "Serie"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{label} gia' importato in libreria (id locale {existing.id})",
        )

    if type == "movie":
        details = tmdb_client.get_movie_details(tmdb_id)
        payload = schemas.SeriesCreate(
            title=details["title"],
            media_type="movie",
            status=series_status,
            runtime=details["runtime"],
            tmdb_id=details["tmdb_id"],
            poster_url=details["poster_url"],
            genres=",".join(details.get("genres") or []) or None,
        )
        return crud.create_series(db, payload)

    details = tmdb_client.get_tv_details(tmdb_id)
    payload = schemas.SeriesCreate(
        title=details["title"],
        media_type="tv",
        status=series_status,
        total_seasons=details["total_seasons"],
        tmdb_id=details["tmdb_id"],
        poster_url=details["poster_url"],
        genres=",".join(details.get("genres") or []) or None,
    )
    series = crud.create_series(db, payload)

    if series.total_seasons:
        all_episodes = []
        for season_number in range(1, series.total_seasons + 1):
            all_episodes.extend(tmdb_client.get_season_episodes(tmdb_id, season_number))
        crud.sync_episodes(db, series.id, all_episodes)

    return series
