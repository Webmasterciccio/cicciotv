"""Endpoint REST per la gestione delle serie TV (per-utente)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import auth, catalog, crud, models, schemas, tmdb_client
from ..database import get_db
from ..models import Status

router = APIRouter(prefix="/series", tags=["series"])


@router.post("", response_model=schemas.SeriesRead, status_code=status.HTTP_201_CREATED)
def create_series(
    payload: schemas.SeriesCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """Aggiungi una nuova serie alla libreria dell'utente."""
    return crud.create_series(db, payload, user_id=user.id)


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
    user: models.User = Depends(auth.get_current_user),
):
    """Elenca le serie dell'utente, opzionalmente filtrate per stato."""
    return crud.list_series(db, user_id=user.id, status=status_filter, skip=skip, limit=limit)


def _get_series_or_404(db: Session, series_id: int, user_id: int) -> models.Series:
    series = crud.get_series(db, series_id, user_id)
    if series is None:
        raise HTTPException(status_code=404, detail="Serie non trovata")
    return series


@router.get("/{series_id}", response_model=schemas.SeriesRead)
def get_series(
    series_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """Dettaglio di una singola serie."""
    return _get_series_or_404(db, series_id, user.id)


@router.patch("/{series_id}", response_model=schemas.SeriesRead)
def update_series(
    series_id: int,
    payload: schemas.SeriesUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """Aggiorna uno o piu' campi di una serie (stato, voto, episodio, ecc.)."""
    series = _get_series_or_404(db, series_id, user.id)
    return crud.update_series(db, series, payload)


@router.delete("/{series_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_series(
    series_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """Rimuovi una serie dalla libreria."""
    series = _get_series_or_404(db, series_id, user.id)
    crud.delete_series(db, series)
    return None


@router.get("/{series_id}/watch-providers", response_model=schemas.WatchProviders)
def watch_providers(
    series_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """Servizi su cui e' possibile guardare la serie (fonte: TMDB, regione IT).
    Disponibile solo per serie/film; per gli altri tipi restituisce vuoto."""
    series = _get_series_or_404(db, series_id, user.id)
    if series.source != "tmdb" or series.tmdb_id is None:
        return schemas.WatchProviders()
    return tmdb_client.get_watch_providers(series.tmdb_id, media_type=series.media_type)


@router.get("/{series_id}/details", response_model=schemas.MediaDetails)
def media_details(
    series_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """Informazioni estese del titolo dalla sua sorgente (trama, generi, autori,
    cast, stagioni/numeri, ecc.)."""
    series = _get_series_or_404(db, series_id, user.id)
    if not series.external_id:
        return schemas.MediaDetails()
    details = catalog.get_details(series.media_type, series.source, series.external_id)

    # Backfill dei generi (per le statistiche/insight) se mancanti in libreria.
    if not series.genres and details.get("genres"):
        series.genres = ",".join(details["genres"])
        db.commit()

    return details


@router.get("/{series_id}/recommendations", response_model=list[schemas.Recommendation])
def recommendations(
    series_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """Titoli consigliati/simili a partire da questo (dalla stessa sorgente)."""
    series = _get_series_or_404(db, series_id, user.id)
    if not series.external_id:
        return []
    return catalog.get_recommendations(series.media_type, series.source, series.external_id)


@router.get("/{series_id}/episodes", response_model=list[schemas.EpisodeRead])
def list_episodes(
    series_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """Elenca gli episodi di una serie con il loro stato di visione."""
    _get_series_or_404(db, series_id, user.id)
    return crud.list_episodes(db, series_id)


@router.post("/{series_id}/episodes/sync", response_model=list[schemas.EpisodeRead])
def sync_episodes(
    series_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """(Ri)scarica le unita' del titolo (episodi anime, numeri fumetti, o episodi
    per stagione delle serie TV). Preserva quelle gia' segnate come viste."""
    series = _get_series_or_404(db, series_id, user.id)

    # Anime (Jikan) e fumetti (Comic Vine): lista piatta di unita' dal dispatcher.
    if series.media_type in ("anime", "comic"):
        if not series.external_id:
            raise HTTPException(status_code=400, detail="Titolo non collegato alla sorgente")
        units = catalog.get_units(series.media_type, series.external_id)
        crud.sync_episodes(db, series_id, units)
        return crud.list_episodes(db, series_id)

    # Serie TV (TMDB): episodi per stagione.
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
    user: models.User = Depends(auth.get_current_user),
):
    """Segna un singolo episodio come visto/non visto. Aggiorna automaticamente lo stato della serie."""
    series = _get_series_or_404(db, series_id, user.id)
    episode = crud.get_episode(db, series_id, episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="Episodio non trovato")
    return crud.set_episode_watched(db, series, episode, payload.watched)


@router.post(
    "/{series_id}/episodes/{episode_id}/watch-up-to",
    response_model=list[schemas.EpisodeRead],
)
def watch_up_to(
    series_id: int,
    episode_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """Segna come visti tutti gli episodi fino a questo incluso (utile quando salti avanti)."""
    series = _get_series_or_404(db, series_id, user.id)
    episode = crud.get_episode(db, series_id, episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="Episodio non trovato")
    return crud.set_watched_up_to(db, series, episode)


@router.patch("/{series_id}/seasons/{season_number}", response_model=list[schemas.EpisodeRead])
def update_season(
    series_id: int,
    season_number: int,
    payload: schemas.EpisodeWatchedUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """Segna tutti gli episodi di una stagione come visti/non visti in blocco."""
    series = _get_series_or_404(db, series_id, user.id)
    return crud.set_season_watched(db, series, season_number, payload.watched)
