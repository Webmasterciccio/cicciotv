"""Endpoint per la ricerca e l'importazione di serie da TMDB."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud, schemas, tmdb_client
from ..database import get_db
from ..models import Status

router = APIRouter(prefix="/tmdb", tags=["tmdb"])


@router.get("/search", response_model=list[schemas.TmdbSearchResult])
def search(query: str = Query(..., min_length=1)):
    """Cerca serie TV su TMDB per titolo."""
    return tmdb_client.search_tv(query)


@router.post(
    "/import/{tmdb_id}",
    response_model=schemas.SeriesRead,
    status_code=status.HTTP_201_CREATED,
)
def import_series(
    tmdb_id: int,
    series_status: Status = Query(default=Status.da_vedere, alias="status"),
    db: Session = Depends(get_db),
):
    """Importa una serie da TMDB nella libreria locale."""
    existing = crud.get_series_by_tmdb_id(db, tmdb_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Serie gia' importata in libreria (id locale {existing.id})",
        )

    details = tmdb_client.get_tv_details(tmdb_id)
    payload = schemas.SeriesCreate(
        title=details["title"],
        status=series_status,
        total_seasons=details["total_seasons"],
        tmdb_id=details["tmdb_id"],
        poster_url=details["poster_url"],
    )
    series = crud.create_series(db, payload)

    if series.total_seasons:
        all_episodes = []
        for season_number in range(1, series.total_seasons + 1):
            all_episodes.extend(tmdb_client.get_season_episodes(tmdb_id, season_number))
        crud.sync_episodes(db, series.id, all_episodes)

    return series
