"""Endpoint per la ricerca e l'importazione di serie da TMDB."""
import random

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import auth, crud, models, schemas, tmdb_client
from ..database import get_db
from ..models import Status

router = APIRouter(prefix="/tmdb", tags=["tmdb"])


MediaType = Query(default="tv", pattern="^(tv|movie)$", description="Tipo: 'tv' o 'movie'")


def _parse_ids(raw: str) -> set[int]:
    """Interpreta una lista di tmdb_id separati da virgola (ignora i non validi)."""
    ids: set[int] = set()
    for part in (raw or "").split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids


def _passes_filters(
    item: dict,
    min_rating: float | None,
    year_from: int | None,
    lang: str | None,
) -> bool:
    """Applica i filtri anche ai consigli seed-based (che TMDB non filtra)."""
    if min_rating is not None:
        if not item.get("vote_average") or item["vote_average"] < min_rating:
            return False
    if year_from is not None:
        date = item.get("first_air_date") or ""
        year = int(date[:4]) if date[:4].isdigit() else 0
        if year < year_from:
            return False
    if lang and item.get("original_language") != lang:
        return False
    return True


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
    sort: str = Query(default="popularity", pattern="^(popularity|rating|recent)$"),
    min_rating: float | None = Query(default=None, ge=0, le=10),
    year_from: int | None = Query(default=None, ge=1900, le=2100),
    lang: str | None = Query(default=None, min_length=2, max_length=2),
    exclude: str = Query(default="", description="tmdb_id gia' mostrati, separati da virgola"),
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """Motore di consigli ibrido: parte dai titoli che ti sono piaciuti
    («perché hai visto X») e completa con i generi preferiti, escludendo la tua
    libreria, i consigli scartati e quelli gia' mostrati, con filtri e varieta'."""
    library = crud.get_library_tmdb_ids(db, user.id, media_type=type)
    dismissed = crud.get_dismissed_ids(db, user.id, type)
    blocked = library | dismissed | _parse_ids(exclude)

    # pool: tmdb_id -> item, con "_score" (numero di semi che lo consigliano).
    pool: dict[int, dict] = {}

    # 1) Consigli basati sui titoli piaciuti (completati o votati alti).
    for seed in crud.get_seed_series(db, user.id, type):
        try:
            recs = tmdb_client.get_recommendations(seed.tmdb_id, media_type=type)
        except HTTPException:
            continue
        for item in recs:
            tid = item["tmdb_id"]
            if tid in blocked:
                continue
            existing = pool.get(tid)
            if existing is None:
                pool[tid] = {**item, "reason": f"Perché hai visto «{seed.title}»", "_score": 1}
            else:
                existing["_score"] += 1

    # 2) Riempimento con i generi preferiti (se i semi non bastano).
    preferred = crud.get_preferred_genres(db, user.id, media_type=type)
    if preferred and len(pool) < limit * 3:
        for page in range(1, 4):
            for item in tmdb_client.discover_by_genres(
                preferred,
                media_type=type,
                page=page,
                sort=sort,
                min_rating=min_rating,
                year_from=year_from,
                lang=lang,
            ):
                tid = item["tmdb_id"]
                if tid in blocked or tid in pool:
                    continue
                pool[tid] = {**item, "reason": None, "_score": 0}
            if len(pool) >= limit * 3:
                break

    # 3) Post-filtri (valgono anche per i consigli seed-based).
    candidates = [
        it for it in pool.values() if _passes_filters(it, min_rating, year_from, lang)
    ]

    # 4) Ordinamento e varieta'.
    if sort == "rating":
        candidates.sort(key=lambda c: c.get("vote_average") or 0, reverse=True)
    elif sort == "recent":
        candidates.sort(key=lambda c: c.get("first_air_date") or "", reverse=True)
    else:
        # Default "consigliati": prima i seed-based (i multi-seme davanti),
        # poi il resto, il tutto mescolato per avere varieta' a ogni visita.
        seeded = [c for c in candidates if c["_score"] > 0]
        others = [c for c in candidates if c["_score"] == 0]
        random.shuffle(seeded)
        seeded.sort(key=lambda c: c["_score"], reverse=True)
        random.shuffle(others)
        candidates = seeded + others

    result = candidates[:limit]
    for c in result:
        c.pop("_score", None)
    return result


@router.post("/suggestions/dismiss", status_code=status.HTTP_204_NO_CONTENT)
def dismiss_suggestion(
    payload: schemas.DismissRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """Scarta un consiglio ('non mi interessa'): non verra' piu' proposto."""
    crud.add_dismissal(db, user.id, payload.media_type, payload.tmdb_id)
    return None


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
    user: models.User = Depends(auth.get_current_user),
):
    """Importa una serie o un film da TMDB nella libreria dell'utente."""
    existing = crud.get_series_by_tmdb_id(db, tmdb_id, user.id, media_type=type)
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
        return crud.create_series(db, payload, user_id=user.id)

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
    series = crud.create_series(db, payload, user_id=user.id)

    if series.total_seasons:
        all_episodes = []
        for season_number in range(1, series.total_seasons + 1):
            all_episodes.extend(tmdb_client.get_season_episodes(tmdb_id, season_number))
        crud.sync_episodes(db, series.id, all_episodes)

    return series
