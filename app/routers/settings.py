"""Endpoint per le preferenze dell'utente (generi preferiti per tipo, per utente)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import auth, crud, models, schemas
from ..database import get_db

router = APIRouter(prefix="/settings", tags=["settings"])


def _current(db: Session, user_id: int) -> schemas.SettingsRead:
    return schemas.SettingsRead(
        preferred_genres_tv=crud.get_preferred_genres(db, user_id, "tv"),
        preferred_genres_movie=crud.get_preferred_genres(db, user_id, "movie"),
        preferred_genres_manga=crud.get_preferred_genres(db, user_id, "manga"),
    )


@router.get("", response_model=schemas.SettingsRead)
def get_settings(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """Legge le preferenze salvate dell'utente (generi preferiti per serie e film)."""
    return _current(db, user.id)


@router.put("", response_model=schemas.SettingsRead)
def update_settings(
    payload: schemas.SettingsUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """Aggiorna le preferenze dell'utente. Si passa solo il tipo da modificare."""
    if payload.preferred_genres_tv is not None:
        crud.set_preferred_genres(db, user.id, "tv", payload.preferred_genres_tv)
    if payload.preferred_genres_movie is not None:
        crud.set_preferred_genres(db, user.id, "movie", payload.preferred_genres_movie)
    if payload.preferred_genres_manga is not None:
        crud.set_preferred_genres(db, user.id, "manga", payload.preferred_genres_manga)
    return _current(db, user.id)
