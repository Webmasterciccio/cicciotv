"""Logica di accesso ai dati (Create, Read, Update, Delete)."""
import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from . import models, schemas
from .models import Status


# Tipi che hanno un elenco di generi a id numerici (TMDB e AniList).
_GENRE_TYPES = ("tv", "movie", "manga")


def _preferred_genres_key(media_type: str) -> str:
    kind = media_type if media_type in _GENRE_TYPES else "tv"
    return f"preferred_genres_{kind}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_series(db: Session, series_id: int, user_id: int) -> Optional[models.Series]:
    """Ritorna la serie solo se appartiene all'utente (altrimenti None)."""
    return (
        db.query(models.Series)
        .filter(models.Series.id == series_id, models.Series.user_id == user_id)
        .first()
    )


def get_series_by_tmdb_id(
    db: Session, tmdb_id: int, user_id: int, media_type: Optional[str] = None
) -> Optional[models.Series]:
    query = db.query(models.Series).filter(
        models.Series.tmdb_id == tmdb_id, models.Series.user_id == user_id
    )
    if media_type is not None:
        query = query.filter(models.Series.media_type == media_type)
    return query.first()


def get_series_by_external(
    db: Session, user_id: int, source: str, external_id: str, media_type: str
) -> Optional[models.Series]:
    """Deduplica per sorgente: un titolo e' unico per (utente, sorgente, id, tipo)."""
    return (
        db.query(models.Series)
        .filter(
            models.Series.user_id == user_id,
            models.Series.source == source,
            models.Series.external_id == str(external_id),
            models.Series.media_type == media_type,
        )
        .first()
    )


def list_series(
    db: Session,
    user_id: int,
    status: Optional[Status] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[models.Series]:
    query = db.query(models.Series).filter(models.Series.user_id == user_id)
    if status is not None:
        query = query.filter(models.Series.status == status)
    return (
        query.order_by(models.Series.title)
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_series(db: Session, data: schemas.SeriesCreate, user_id: int) -> models.Series:
    series = models.Series(**data.model_dump(), user_id=user_id)
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
    elif "progress_current" in changes:
        # Manga/libri: lo stato segue il progresso (letto/in lettura) se non e'
        # stato impostato esplicitamente nella stessa richiesta.
        _sync_progress_status(series, previous_status=previous_status)

    db.commit()
    db.refresh(series)
    return series


def _sync_progress_status(series: models.Series, previous_status) -> None:
    """Deriva lo stato dal progresso a pagine/capitoli per i tipi senza episodi."""
    current = series.progress_current or 0
    total = series.progress_total or 0
    if total and current >= total:
        series.status = Status.vista
    elif current > 0:
        series.status = Status.in_corso
    if series.status != previous_status:
        _sync_watch_dates(series, previous_status=previous_status)


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


def get_tv_watch_progress(db: Session, series_ids: list[int]) -> dict[int, dict]:
    """Per ogni serie, se e' 'in pari' (nessun episodio gia' uscito rimasto da
    vedere: gli episodi futuri noti non contano contro l'utente) e la data del
    prossimo episodio non ancora uscito, se nota. Solo per serie con almeno un
    episodio sincronizzato (altrimenti 'in pari' non e' significativo)."""
    if not series_ids:
        return {}
    today = _now().date().isoformat()
    episodes = (
        db.query(models.Episode)
        .filter(models.Episode.series_id.in_(series_ids))
        .all()
    )
    by_series: dict[int, list[models.Episode]] = {}
    for ep in episodes:
        by_series.setdefault(ep.series_id, []).append(ep)

    result: dict[int, dict] = {}
    for series_id, eps in by_series.items():
        unwatched_released = [
            e for e in eps if not e.watched and (not e.air_date or e.air_date <= today)
        ]
        future_dates = sorted(
            e.air_date for e in eps if not e.watched and e.air_date and e.air_date > today
        )
        result[series_id] = {
            "caught_up": len(unwatched_released) == 0,
            "next_episode_air_date": future_dates[0] if future_dates else None,
        }
    return result


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
    # Campi arricchiti da TMDB da tenere sempre allineati (non toccano 'watched').
    detail_fields = ("name", "overview", "still_url", "air_date", "vote_average", "runtime")
    for data in episodes_data:
        key = (data["season_number"], data["episode_number"])
        episode = existing.get(key)
        if episode is not None:
            for field in detail_fields:
                if field in data:
                    setattr(episode, field, data.get(field))
        else:
            db.add(
                models.Episode(
                    series_id=series_id,
                    season_number=data["season_number"],
                    episode_number=data["episode_number"],
                    **{f: data.get(f) for f in detail_fields},
                )
            )
    db.query(models.Series).filter(models.Series.id == series_id).update(
        {"episodes_synced_at": _now()}
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


def set_watched_up_to(
    db: Session, series: models.Series, target: models.Episode
) -> list[models.Episode]:
    """Segna come visti tutti gli episodi fino a 'target' incluso (ordine stagione/episodio)."""
    now = _now()
    target_key = (target.season_number, target.episode_number)
    for episode in list_episodes(db, series.id):
        if (episode.season_number, episode.episode_number) <= target_key and not episode.watched:
            episode.watched = True
            episode.watched_at = now
    db.commit()
    _recompute_series_progress(db, series)
    return list_episodes(db, series.id)


# --- Impostazioni ---


def get_user_setting(db: Session, user_id: int, key: str) -> Optional[str]:
    setting = db.get(models.UserSetting, (user_id, key))
    return setting.value if setting else None


def set_user_setting(db: Session, user_id: int, key: str, value: Optional[str]) -> None:
    setting = db.get(models.UserSetting, (user_id, key))
    if setting is None:
        setting = models.UserSetting(user_id=user_id, key=key, value=value)
        db.add(setting)
    else:
        setting.value = value
    db.commit()


def get_preferred_genres(db: Session, user_id: int, media_type: str = "tv") -> list[int]:
    raw = get_user_setting(db, user_id, _preferred_genres_key(media_type))
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return [int(x) for x in data]
    except (ValueError, TypeError):
        return []


def set_preferred_genres(
    db: Session, user_id: int, media_type: str, genre_ids: list[int]
) -> list[int]:
    cleaned = [int(x) for x in genre_ids]
    set_user_setting(db, user_id, _preferred_genres_key(media_type), json.dumps(cleaned))
    return cleaned


def get_library_tmdb_ids(
    db: Session, user_id: int, media_type: Optional[str] = None
) -> set[int]:
    query = db.query(models.Series.tmdb_id).filter(
        models.Series.tmdb_id.isnot(None), models.Series.user_id == user_id
    )
    if media_type is not None:
        query = query.filter(models.Series.media_type == media_type)
    return {r[0] for r in query.all()}


def get_library_external_ids(db: Session, user_id: int, media_type: str) -> set[str]:
    """External_id (stringa) dei titoli in libreria per quel tipo: serve a non
    riproporre nei consigli cio' che l'utente ha gia'."""
    rows = (
        db.query(models.Series.external_id)
        .filter(
            models.Series.user_id == user_id,
            models.Series.media_type == media_type,
            models.Series.external_id.isnot(None),
        )
        .all()
    )
    return {r[0] for r in rows}


# Voto minimo perche' un titolo in libreria sia considerato "piaciuto" (seme).
_SEED_MIN_RATING = 7


def get_seed_series(
    db: Session, user_id: int, media_type: str, limit: int = 8
) -> list[models.Series]:
    """Titoli 'piaciuti' dall'utente usati come semi per i consigli:
    completati (status=vista) oppure votati alti. Solo quelli con tmdb_id."""
    query = (
        db.query(models.Series)
        .filter(
            models.Series.user_id == user_id,
            models.Series.media_type == media_type,
            models.Series.external_id.isnot(None),
        )
        .filter(
            (models.Series.status == Status.vista)
            | (models.Series.rating >= _SEED_MIN_RATING)
        )
    )
    # I preferiti prima: voto piu' alto, poi finiti di recente.
    rows = query.all()
    rows.sort(
        key=lambda s: (s.rating or 0, s.finished_at or s.updated_at or _now()),
        reverse=True,
    )
    return rows[:limit]


def get_dismissed_ids(db: Session, user_id: int, media_type: str) -> set[str]:
    rows = (
        db.query(models.Dismissal.external_id)
        .filter(
            models.Dismissal.user_id == user_id,
            models.Dismissal.media_type == media_type,
        )
        .all()
    )
    return {r[0] for r in rows}


def add_dismissal(
    db: Session, user_id: int, media_type: str, source: str, external_id: str
) -> None:
    key = (user_id, media_type, source, str(external_id))
    if db.get(models.Dismissal, key) is None:
        db.add(
            models.Dismissal(
                user_id=user_id,
                media_type=media_type,
                source=source,
                external_id=str(external_id),
            )
        )
        db.commit()


# --- Statistiche ---


def _episodes_per_month(watched: list[models.Episode], max_months: int = 12) -> list[dict]:
    """Conta gli episodi visti per mese, su una serie continua di mesi (con zeri)."""
    counts: dict[str, int] = {}
    for e in watched:
        if e.watched_at is None:
            continue
        key = e.watched_at.strftime("%Y-%m")
        counts[key] = counts.get(key, 0) + 1
    if not counts:
        return []

    first = min(counts)
    now = datetime.now(timezone.utc)
    year, month = int(first[:4]), int(first[5:7])
    result: list[dict] = []
    while (year, month) <= (now.year, now.month):
        key = f"{year:04d}-{month:02d}"
        result.append({"month": key, "count": counts.get(key, 0)})
        month += 1
        if month > 12:
            month = 1
            year += 1
    return result[-max_months:]


_WEEKDAYS_IT = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]


def _fmt_days(d: int) -> str:
    if d <= 0:
        return "in giornata"
    if d == 1:
        return "in 1 giorno"
    return f"in {d} giorni"


def _watch_insights(tv_series: list, episodes: list) -> tuple[list[str], list[dict]]:
    """Genera frasi-insight sulle abitudini di visione e la distribuzione per
    giorno della settimana, a partire da quando gli episodi sono stati segnati visti."""
    from collections import defaultdict

    watched = [e for e in episodes if e.watched and e.watched_at]
    weekday_counts = [0] * 7
    weekday_data = [{"weekday": i, "count": 0} for i in range(7)]
    if not watched:
        return [], weekday_data

    hour_counts = [0] * 24
    day_counts: dict = defaultdict(int)
    by_series: dict = defaultdict(list)
    for e in watched:
        t = e.watched_at
        weekday_counts[t.weekday()] += 1
        hour_counts[t.hour] += 1
        day_counts[t.date()] += 1
        by_series[e.series_id].append(t)

    title_by_id = {s.id: s.title for s in tv_series}
    completed = [s for s in tv_series if s.status == Status.vista]

    # Tempo di completamento (giorni) per le serie finite con almeno 2 episodi datati.
    spans: dict = {}
    for s in completed:
        times = by_series.get(s.id, [])
        if len(times) >= 2:
            spans[s.id] = (max(times) - min(times)).days

    insights: list[str] = []

    # 1) Genere completato piu' in fretta.
    genre_days: dict = defaultdict(list)
    for s in completed:
        if s.id in spans and s.genres:
            for g in (x.strip() for x in s.genres.split(",")):
                if g:
                    genre_days[g].append(spans[s.id])
    if genre_days:
        avg_by_genre = {g: sum(v) / len(v) for g, v in genre_days.items()}
        fastest = min(avg_by_genre, key=avg_by_genre.get)
        avg = round(avg_by_genre[fastest])
        if avg <= 7:
            insights.append(f"🍿 Le serie {fastest} le divori: in media in meno di una settimana!")
        else:
            insights.append(f"🎬 Le serie {fastest} le finisci in media in {avg} giorni.")

    # 2) Maratona piu' veloce.
    if spans:
        sid = min(spans, key=spans.get)
        d = spans[sid]
        title = title_by_id.get(sid, "?")
        if d <= 7:
            insights.append(
                f"⚡ Maratona record: «{title}» vista {_fmt_days(d)} (meno di una settimana)!"
            )
        else:
            insights.append(f"🏁 «{title}» completata {_fmt_days(d)}.")

    # 3) Giorno con piu' episodi.
    day, n = max(day_counts.items(), key=lambda kv: kv[1])
    if n >= 3:
        insights.append(f"🔥 Record: {n} episodi in un solo giorno ({day.strftime('%d/%m')})!")

    # 4) Giorno della settimana preferito.
    if sum(weekday_counts) >= 5:
        wd = max(range(7), key=lambda i: weekday_counts[i])
        insights.append(f"📅 Guardi soprattutto di {_WEEKDAYS_IT[wd]}.")

    # 5) Fascia oraria preferita.
    if sum(hour_counts) >= 5:
        fasce = {"di mattina": 0, "di pomeriggio": 0, "di sera": 0, "di notte": 0}
        for h, c in enumerate(hour_counts):
            if 5 <= h < 12:
                fasce["di mattina"] += c
            elif 12 <= h < 18:
                fasce["di pomeriggio"] += c
            elif 18 <= h < 23:
                fasce["di sera"] += c
            else:
                fasce["di notte"] += c
        top = max(fasce, key=fasce.get)
        emoji = {"di mattina": "☀️", "di pomeriggio": "🌤️", "di sera": "🌆", "di notte": "🌙"}[top]
        insights.append(f"{emoji} Sei da binge {top}.")

    weekday_data = [{"weekday": i, "count": weekday_counts[i]} for i in range(7)]
    return insights, weekday_data


def compute_stats(db: Session, user_id: int) -> dict:
    """Calcola le statistiche della libreria dell'utente a partire dai dati locali."""
    all_media = db.query(models.Series).filter(models.Series.user_id == user_id).all()
    # Le sezioni "Serie TV" e "Film" restano sui rispettivi tipi; gli altri
    # (anime, manga, libri, fumetti) sono riepilogati nella panoramica per tipo.
    series = [s for s in all_media if s.media_type == "tv"]
    movies = [s for s in all_media if s.media_type == "movie"]
    episodes = (
        db.query(models.Episode)
        .join(models.Series, models.Episode.series_id == models.Series.id)
        .filter(models.Series.user_id == user_id, models.Series.media_type == "tv")
        .all()
    )

    # Panoramica per tipo (tutti i tipi presenti in libreria).
    by_type = []
    for t in ("tv", "movie", "manga", "book", "comic"):
        items = [s for s in all_media if s.media_type == t]
        if not items:
            continue
        type_ratings = [s.rating for s in items if s.rating is not None]
        by_type.append(
            {
                "media_type": t,
                "total": len(items),
                "to_watch": sum(1 for s in items if s.status == Status.da_vedere),
                "in_progress": sum(1 for s in items if s.status == Status.in_corso),
                "completed": sum(1 for s in items if s.status == Status.vista),
                "average_rating": round(sum(type_ratings) / len(type_ratings), 1)
                if type_ratings
                else None,
            }
        )

    watched = [e for e in episodes if e.watched]
    ratings = [s.rating for s in series if s.rating is not None]

    # Statistiche film.
    movies_watched = [m for m in movies if m.status == Status.vista]
    movie_ratings = [m.rating for m in movies if m.rating is not None]

    # Film visti questo mese, per luogo (in base a finished_at).
    now = datetime.now(timezone.utc)
    this_month = {"cinema": 0, "streaming": 0, "tv": 0, "total": 0}
    for m in movies_watched:
        fa = m.finished_at
        if fa is None or fa.year != now.year or fa.month != now.month:
            continue
        this_month["total"] += 1
        if m.watch_location in ("cinema", "streaming", "tv"):
            this_month[m.watch_location] += 1

    movies_stats = {
        "total": len(movies),
        "to_watch": sum(1 for m in movies if m.status != Status.vista),
        "watched": len(movies_watched),
        "minutes_watched": sum(m.runtime or 0 for m in movies_watched),
        "average_rating": round(sum(movie_ratings) / len(movie_ratings), 1)
        if movie_ratings
        else None,
        "rated_count": len(movie_ratings),
        "this_month": this_month,
    }

    # Episodi visti/totali per serie.
    watched_by_series: dict[int, int] = {}
    total_by_series: dict[int, int] = {}
    for e in episodes:
        total_by_series[e.series_id] = total_by_series.get(e.series_id, 0) + 1
        if e.watched:
            watched_by_series[e.series_id] = watched_by_series.get(e.series_id, 0) + 1

    title_by_id = {s.id: s.title for s in series}
    top_series = sorted(watched_by_series.items(), key=lambda kv: kv[1], reverse=True)[:5]

    in_progress = []
    for s in series:
        if s.status != Status.in_corso:
            continue
        total = total_by_series.get(s.id, 0)
        seen = watched_by_series.get(s.id, 0)
        in_progress.append(
            {
                "id": s.id,
                "title": s.title,
                "watched": seen,
                "total": total,
                "percent": round(seen / total * 100) if total else 0,
            }
        )
    in_progress.sort(key=lambda x: x["percent"], reverse=True)

    watch_insights, episodes_by_weekday = _watch_insights(series, episodes)

    return {
        "total_series": len(series),
        "to_watch": sum(1 for s in series if s.status == Status.da_vedere),
        "watching": sum(1 for s in series if s.status == Status.in_corso),
        "completed": sum(1 for s in series if s.status == Status.vista),
        "total_episodes": len(episodes),
        "episodes_watched": len(watched),
        "minutes_watched": sum(e.runtime or 0 for e in watched),
        "average_rating": round(sum(ratings) / len(ratings), 1) if ratings else None,
        "rated_count": len(ratings),
        "top_series": [
            {"id": sid, "title": title_by_id.get(sid, "?"), "episodes_watched": count}
            for sid, count in top_series
        ],
        "episodes_per_month": _episodes_per_month(watched),
        "in_progress": in_progress,
        "movies": movies_stats,
        "watch_insights": watch_insights,
        "episodes_by_weekday": episodes_by_weekday,
        "by_type": by_type,
    }


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
            # Se la fonte dice che e' ancora in produzione, "visto tutto il
            # rilasciato finora" non vuol dire "conclusa": resta in_corso
            # (compare come "in pari" in libreria). still_airing=None (fonte
            # sconosciuta/righe precedenti a questo campo) mantiene il
            # comportamento di prima (passa a vista).
            series.status = Status.in_corso if series.still_airing else Status.vista
        elif series.status in (Status.da_vedere, Status.vista):
            series.status = Status.in_corso
    elif series.status == Status.vista:
        series.status = Status.in_corso

    if series.status != previous_status:
        _sync_watch_dates(series, previous_status=previous_status)

    db.commit()
    db.refresh(series)
