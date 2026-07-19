"""Logica di accesso ai dati (Create, Read, Update, Delete)."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from . import models, schemas
from .models import Status


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_series(db: Session, series_id: int) -> Optional[models.Series]:
    return db.get(models.Series, series_id)


def get_series_by_tmdb_id(db: Session, tmdb_id: int) -> Optional[models.Series]:
    return db.query(models.Series).filter(models.Series.tmdb_id == tmdb_id).first()


def list_series(
    db: Session,
    status: Optional[Status] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[models.Series]:
    query = db.query(models.Series)
    if status is not None:
        query = query.filter(models.Series.status == status)
    return (
        query.order_by(models.Series.title)
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_series(db: Session, data: schemas.SeriesCreate) -> models.Series:
    series = models.Series(**data.model_dump())
    _sync_watch_dates(series, previous_status=None)
    db.add(series)
    db.commit()
    db.refresh(series)
    return series


def update_series(
    db: Session, series: models.Series, data: schemas.SeriesUpdate
) -> models.Series:
    previous_status = series.status
    # exclude_unset: aggiorna solo i campi effettivamente passati nella richiesta.
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(series, field, value)

    if "status" in changes:
        _sync_watch_dates(series, previous_status=previous_status)

    db.commit()
    db.refresh(series)
    return series


def delete_series(db: Session, series: models.Series) -> None:
    db.query(models.Episode).filter(models.Episode.series_id == series.id).delete()
    db.delete(series)
    db.commit()


def _sync_watch_dates(series: models.Series, previous_status) -> None:
    """Imposta automaticamente started_at / finished_at in base al cambio di stato."""
    if series.status == Status.in_corso and series.started_at is None:
        series.started_at = _now()
    if series.status == Status.vista and series.finished_at is None:
        series.finished_at = _now()
        if series.started_at is None:
            series.started_at = _now()


# --- Episodi ---


def list_episodes(db: Session, series_id: int) -> list[models.Episode]:
    return (
        db.query(models.Episode)
        .filter(models.Episode.series_id == series_id)
        .order_by(models.Episode.season_number, models.Episode.episode_number)
        .all()
    )


def get_episode(db: Session, series_id: int, episode_id: int) -> Optional[models.Episode]:
    return (
        db.query(models.Episode)
        .filter(models.Episode.id == episode_id, models.Episode.series_id == series_id)
        .first()
    )


def sync_episodes(db: Session, series_id: int, episodes_data: list[dict]) -> None:
    """Crea gli episodi mancanti da TMDB; preserva lo stato 'watched' di quelli gia' presenti."""
    existing = {
        (e.season_number, e.episode_number): e for e in list_episodes(db, series_id)
    }
    for data in episodes_data:
        key = (data["season_number"], data["episode_number"])
        episode = existing.get(key)
        if episode is not None:
            episode.name = data.get("name")
        else:
            db.add(
                models.Episode(
                    series_id=series_id,
                    season_number=data["season_number"],
                    episode_number=data["episode_number"],
                    name=data.get("name"),
                )
            )
    db.commit()


def set_episode_watched(
    db: Session, series: models.Series, episode: models.Episode, watched: bool
) -> models.Episode:
    episode.watched = watched
    episode.watched_at = _now() if watched else None
    db.commit()
    _recompute_series_progress(db, series)
    db.refresh(episode)
    return episode


def set_season_watched(
    db: Session, series: models.Series, season_number: int, watched: bool
) -> list[models.Episode]:
    episodes = (
        db.query(models.Episode)
        .filter(
            models.Episode.series_id == series.id,
            models.Episode.season_number == season_number,
        )
        .all()
    )
    now = _now()
    for episode in episodes:
        episode.watched = watched
        episode.watched_at = now if watched else None
    db.commit()
    _recompute_series_progress(db, series)
    return list_episodes(db, series.id)


def _recompute_series_progress(db: Session, series: models.Series) -> None:
    """Aggiorna stagione/episodio corrente e lo stato della serie in base agli episodi visti."""
    episodes = list_episodes(db, series.id)
    if not episodes:
        return

    watched_episodes = [e for e in episodes if e.watched]
    previous_status = series.status

    if watched_episodes:
        latest = max(watched_episodes, key=lambda e: (e.season_number, e.episode_number))
        series.current_season = latest.season_number
        series.current_episode = latest.episode_number

        if len(watched_episodes) == len(episodes):
            series.status = Status.vista
        elif series.status in (Status.da_vedere, Status.vista):
            series.status = Status.in_corso
    elif series.status == Status.vista:
        series.status = Status.in_corso

    if series.status != previous_status:
        _sync_watch_dates(series, previous_status=previous_status)

    db.commit()
    db.refresh(series)
