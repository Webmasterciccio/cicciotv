"""Endpoint multi-sorgente: ricerca, generi, consigli e importazione per tutti i
tipi di media (serie/film via TMDB, anime/manga via Jikan, libri via Google
Books, fumetti via Comic Vine). Instrada tramite il dispatcher ``catalog``."""
import random

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import auth, catalog, crud, models, schemas
from ..database import get_db

router = APIRouter(prefix="/catalog", tags=["catalog"])

MediaType = Query(
    default="tv",
    pattern="^(tv|movie|anime|manga|book|comic)$",
    description="tv, movie, anime, manga, book, comic",
)

# Tipi che si "guardano" (verbo dei consigli) vs quelli che si "leggono".
_WATCH_TYPES = {"tv", "movie", "anime"}


def _reason_verb(media_type: str) -> str:
    return "visto" if media_type in _WATCH_TYPES else "letto"


def _parse_ids(raw: str) -> set[str]:
    """Interpreta una lista di external_id (stringhe) separati da virgola."""
    return {p.strip() for p in (raw or "").split(",") if p.strip()}


def _passes_filters(item: dict, min_rating, year_from, lang) -> bool:
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


@router.get("/search", response_model=list[schemas.SearchResult])
def search(query: str = Query(..., min_length=1), type: str = MediaType):
    """Cerca titoli sulla sorgente giusta per il tipo."""
    return catalog.search(query, type)


@router.get("/genres", response_model=list[schemas.Genre])
def genres(type: str = MediaType):
    """Elenco generi per scegliere le preferenze (vuoto per libri/fumetti)."""
    return catalog.get_genres(type)


@router.get("/details", response_model=schemas.MediaDetails)
def preview_details(
    source: str = Query(..., description="Sorgente del titolo"),
    external_id: str = Query(..., description="Id presso la sorgente"),
    type: str = MediaType,
):
    """Dettagli estesi di un titolo NON ancora in libreria (per l'anteprima
    prima dell'aggiunta): trama, generi, autori, dati specifici del tipo."""
    return catalog.get_details(type, source, external_id)


@router.get("/suggestions", response_model=list[schemas.Recommendation])
def suggestions(
    limit: int = Query(default=20, ge=1, le=40),
    type: str = MediaType,
    sort: str = Query(default="popularity", pattern="^(popularity|rating|recent)$"),
    min_rating: float | None = Query(default=None, ge=0, le=10),
    year_from: int | None = Query(default=None, ge=1000, le=2100),
    lang: str | None = Query(default=None, min_length=2, max_length=2),
    exclude: str = Query(default="", description="external_id gia' mostrati, separati da virgola"),
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """Motore di consigli ibrido e multi-sorgente: parte dai titoli piaciuti
    («perché hai visto/letto X»), completa con generi preferiti o popolari,
    esclude libreria/scartati/gia' mostrati, applica filtri e mescola."""
    media_type = type
    blocked = (
        crud.get_library_external_ids(db, user.id, media_type)
        | crud.get_dismissed_ids(db, user.id, media_type)
        | _parse_ids(exclude)
    )
    verb = _reason_verb(media_type)

    # pool: external_id -> item (con "_score" = numero di semi che lo consigliano).
    pool: dict[str, dict] = {}

    # 1) Consigli basati sui titoli piaciuti (completati o votati alti).
    for seed in crud.get_seed_series(db, user.id, media_type):
        try:
            recs = catalog.get_recommendations(media_type, seed.source, seed.external_id)
        except HTTPException:
            continue
        for item in recs:
            tid = item.get("external_id")
            if not tid or tid in blocked:
                continue
            existing = pool.get(tid)
            if existing is None:
                pool[tid] = {**item, "reason": f"Perché hai {verb} «{seed.title}»", "_score": 1}
            else:
                existing["_score"] += 1

    # 2) Riempimento: generi preferiti (tv/movie/anime/manga) o popolari.
    if len(pool) < limit * 3:
        preferred = crud.get_preferred_genres(db, user.id, media_type)
        if preferred:
            for page in range(1, 4):
                for item in catalog.discover(
                    media_type, preferred, page=page, sort=sort,
                    min_rating=min_rating, year_from=year_from, lang=lang,
                ):
                    tid = item.get("external_id")
                    if not tid or tid in blocked or tid in pool:
                        continue
                    pool[tid] = {**item, "reason": None, "_score": 0}
                if len(pool) >= limit * 3:
                    break
        else:
            for page in range(1, 3):
                for item in catalog.get_popular(media_type, page=page):
                    tid = item.get("external_id")
                    if not tid or tid in blocked or tid in pool:
                        continue
                    pool[tid] = {**item, "reason": None, "_score": 0}
                if len(pool) >= limit * 3:
                    break

    # 3) Post-filtri (valgono anche per i consigli seed-based).
    candidates = [it for it in pool.values() if _passes_filters(it, min_rating, year_from, lang)]

    # 4) Ordinamento e varieta'.
    if sort == "rating":
        candidates.sort(key=lambda c: c.get("vote_average") or 0, reverse=True)
    elif sort == "recent":
        candidates.sort(key=lambda c: c.get("first_air_date") or "", reverse=True)
    else:
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
    crud.add_dismissal(db, user.id, payload.media_type, payload.source, payload.external_id)
    return None


@router.post("/import", response_model=schemas.SeriesRead, status_code=status.HTTP_201_CREATED)
def import_item(
    payload: schemas.ImportRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """Importa un titolo di qualsiasi sorgente nella libreria dell'utente."""
    existing = crud.get_series_by_external(
        db, user.id, payload.source, payload.external_id, payload.media_type
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Titolo gia' in libreria (id locale {existing.id})",
        )

    create_payload, units = catalog.build_import(
        payload.media_type, payload.source, payload.external_id
    )
    create_payload.status = payload.status
    series = crud.create_series(db, create_payload, user_id=user.id)
    if units:
        crud.sync_episodes(db, series.id, units)
    return series
