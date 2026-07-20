"""Endpoint per le preferenze dell'utente (generi preferiti per tipo)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/settings", tags=["settings"])


def _current(db: Session) -> schemas.SettingsRead:
    return schemas.SettingsRead(
        preferred_genres_tv=crud.get_preferred_genres(db, "tv"),
        preferred_genres_movie=crud.get_preferred_genres(db, "movie"),
    )


@router.get("", response_model=schemas.SettingsRead)
def get_settings(db: Session = Depends(get_db)):
    """Legge le preferenze salvate (generi preferiti per serie e film)."""
    return _current(db)


@router.put("", response_model=schemas.SettingsRead)
def update_settings(payload: schemas.SettingsUpdate, db: Session = Depends(get_db)):
    """Aggiorna le preferenze. Si passa solo il tipo che si vuole modificare."""
    if payload.preferred_genres_tv is not None:
        crud.set_preferred_genres(db, "tv", payload.preferred_genres_tv)
    if payload.preferred_genres_movie is not None:
        crud.set_preferred_genres(db, "movie", payload.preferred_genres_movie)
    return _current(db)
