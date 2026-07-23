"""Endpoint per le statistiche della libreria (per-utente)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import auth, crud, models, schemas, tmdb_client
from ..database import get_db
from ..models import Status

router = APIRouter(prefix="/stats", tags=["stats"])


def _backfill_genres(db: Session, user_id: int) -> None:
    """Recupera da TMDB i generi mancanti delle serie completate dell'utente
    (servono per gli insight per genere). Poche chiamate: solo serie 'viste' senza generi."""
    pending = (
        db.query(models.Series)
        .filter(
            models.Series.user_id == user_id,
            models.Series.status == Status.vista,
            models.Series.media_type != "movie",
            models.Series.tmdb_id.isnot(None),
            models.Series.genres.is_(None),
        )
        .all()
    )
    changed = False
    for s in pending:
        try:
            details = tmdb_client.get_tv_details(s.tmdb_id)
        except Exception:
            continue
        genres = details.get("genres") or []
        if genres:
            s.genres = ",".join(genres)
            changed = True
    if changed:
        db.commit()


@router.get("", response_model=schemas.Stats)
def get_stats(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """Statistiche riepilogative sulla libreria dell'utente (serie, film, episodi, abitudini)."""
    _backfill_genres(db, user.id)
    return crud.compute_stats(db, user.id)
