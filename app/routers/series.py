"""Endpoint REST per la gestione delle serie TV."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud, schemas, tmdb_client
from ..database import get_db
from ..models import Status

router = APIRouter(prefix="/series", tags=["series"])


@router.post("", response_model=schemas.SeriesRead, status_code=status.HTTP_201_CREATED)
def create_series(payload: schemas.SeriesCreate, db: Session = Depends(get_db)):
    """Aggiungi una nuova serie alla libreria."""
    return crud.create_series(db, payload)


@router.get("", response_model=list[schemas.SeriesRead])
def list_series(
    status_filter: Optional[Status] = Query(
        default=None,
        alias="status",
        description="Filtra per stato: da_vedere, in_corso, vista",
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Elenca le serie, opzionalmente filtrate per stato."""
    return crud.list_series(db, status=status_filter, skip=skip, limit=limit)


@router.get("/{series_id}", response_model=schemas.SeriesRead)
def get_series(series_id: int, db: Session = Depends(get_db)):
    """Dettaglio di una singola serie."""
    series = crud.get_series(db, series_id)
    if series is None:
        raise HTTPException(status_code=404, detail="Serie non trovata")
    return series


@router.patch("/{series_id}", response_model=schemas.SeriesRead)
def update_series(
    series_id: int, payload: schemas.SeriesUpdate, db: Session = Depends(get_db)
):
    """Aggiorna uno o piu' campi di una serie (stato, voto, episodio, ecc.)."""
    series = crud.get_series(db, series_id)
    if series is None:
        raise HTTPException(status_code=404, detail="Serie non trovata")
    return crud.update_series(db, series, payload)


@router.delete("/{series_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_series(series_id: int, db: Session = Depends(get_db)):
    """Rimuovi una serie dalla libreria."""
    series = crud.get_series(db, series_id)
    if series is None:
        raise HTTPException(status_code=404, detail="Serie non trovata")
    crud.delete_series(db, series)
    return None


def _get_series_or_404(db: Session, series_id: int):
    series = crud.get_series(db, series_id)
    if series is None:
        raise HTTPException(status_code=404, detail="Serie non trovata")
    return series


@router.get("/{series_id}/episodes", response_model=list[schemas.EpisodeRead])
def list_episodes(series_id: int, db: Session = Depends(get_db)):
    """Elenca gli episodi di una serie con il loro stato di visione."""
    _get_series_or_404(db, series_id)
    return crud.list_episodes(db, series_id)


@router.post("/{series_id}/episodes/sync", response_model=list[schemas.EpisodeRead])
def sync_episodes(series_id: int, db: Session = Depends(get_db)):
    """(Ri)scarica da TMDB l'elenco degli episodi di tutte le stagioni. Preserva quelli gia' segnati come visti."""
    series = _get_series_or_404(db, series_id)
    if series.tmdb_id is None:
        raise HTTPException(
            status_code=400,
            detail="Serie non collegata a TMDB: sincronizzazione episodi non disponibile",
        )
    if not series.total_seasons:
        raise HTTPException(status_code=400, detail="Numero di stagioni sconosciuto")

    all_episodes = []
    for season_number in range(1, series.total_seasons + 1):
        all_episodes.extend(tmdb_client.get_season_episodes(series.tmdb_id, season_number))
    crud.sync_episodes(db, series_id, all_episodes)
    return crud.list_episodes(db, series_id)


@router.patch("/{series_id}/episodes/{episode_id}", response_model=schemas.EpisodeRead)
def update_episode(
    series_id: int,
    episode_id: int,
    payload: schemas.EpisodeWatchedUpdate,
    db: Session = Depends(get_db),
):
    """Segna un singolo episodio come visto/non visto. Aggiorna automaticamente lo stato della serie."""
    series = _get_series_or_404(db, series_id)
    episode = crud.get_episode(db, series_id, episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="Episodio non trovato")
    return crud.set_episode_watched(db, series, episode, payload.watched)


@router.patch("/{series_id}/seasons/{season_number}", response_model=list[schemas.EpisodeRead])
def update_season(
    series_id: int,
    season_number: int,
    payload: schemas.EpisodeWatchedUpdate,
    db: Session = Depends(get_db),
):
    """Segna tutti gli episodi di una stagione come visti/non visti in blocco."""
    series = _get_series_or_404(db, series_id)
    return crud.set_season_watched(db, series, season_number, payload.watched)
