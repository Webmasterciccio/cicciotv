"""Backup della libreria personale: esportazione e importazione (per utente).

Il file esportato contiene solo i dati dell'utente che lo ha generato (titoli,
episodi/volumi visti, preferenze), pensato come backup personale o per
trasferire la propria libreria su un'altra installazione."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import auth, crud, models, schemas
from ..database import get_db

router = APIRouter(prefix="/backup", tags=["backup"])


@router.get("/export", response_model=schemas.LibraryExport)
def export_library(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    series_export = []
    for s in crud.list_series(db, user_id=user.id, limit=100_000):
        episodes = crud.list_episodes(db, s.id)
        series_export.append(
            schemas.SeriesExport(
                **schemas.SeriesBase.model_validate(s).model_dump(),
                started_at=s.started_at,
                finished_at=s.finished_at,
                episodes=[schemas.EpisodeExport.model_validate(e) for e in episodes],
            )
        )
    return schemas.LibraryExport(
        exported_at=datetime.now(timezone.utc),
        series=series_export,
        preferred_genres_tv=crud.get_preferred_genres(db, user.id, "tv"),
        preferred_genres_movie=crud.get_preferred_genres(db, user.id, "movie"),
        preferred_genres_manga=crud.get_preferred_genres(db, user.id, "manga"),
    )


def _find_duplicate(db: Session, user_id: int, item: schemas.SeriesExport):
    if item.external_id:
        return crud.get_series_by_external(
            db, user_id, item.source, item.external_id, item.media_type
        )
    # Senza id esterno (raro), l'unico riferimento possibile e' il titolo.
    return (
        db.query(models.Series)
        .filter(
            models.Series.user_id == user_id,
            models.Series.media_type == item.media_type,
            models.Series.title.ilike(item.title),
        )
        .first()
    )


@router.post("/import", response_model=schemas.ImportResult)
def import_library(
    payload: schemas.LibraryExport,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """Importa un file esportato in precedenza. I titoli gia' presenti in
    libreria (stessa fonte+id, o stesso titolo/tipo se manca l'id esterno)
    vengono lasciati intatti: si aggiungono solo quelli mancanti."""
    imported = 0
    skipped = 0
    for item in payload.series:
        if _find_duplicate(db, user.id, item) is not None:
            skipped += 1
            continue

        series = models.Series(
            **item.model_dump(exclude={"episodes", "started_at", "finished_at"}),
            user_id=user.id,
            started_at=item.started_at,
            finished_at=item.finished_at,
        )
        db.add(series)
        db.flush()  # per avere series.id senza dover fare un commit a parte
        for ep in item.episodes:
            db.add(models.Episode(series_id=series.id, **ep.model_dump()))
        imported += 1

    # Le preferenze si applicano solo se l'utente non ne ha gia' impostate,
    # per non sovrascrivere scelte fatte dopo il backup.
    for media_type, values in (
        ("tv", payload.preferred_genres_tv),
        ("movie", payload.preferred_genres_movie),
        ("manga", payload.preferred_genres_manga),
    ):
        if values and not crud.get_preferred_genres(db, user.id, media_type):
            crud.set_preferred_genres(db, user.id, media_type, values)

    db.commit()
    return schemas.ImportResult(imported=imported, skipped=skipped)
