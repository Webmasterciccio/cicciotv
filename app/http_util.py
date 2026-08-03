"""Utilita' HTTP condivise dai client delle API esterne.

Fornisce un GET JSON con:
- cache in memoria a scadenza (TTL), per non ripetere le stesse chiamate e per
  alleggerire le API con rate limit stretti (Jikan, Comic Vine);
- un throttle opzionale per-servizio (intervallo minimo tra due chiamate);
- gestione uniforme degli errori come HTTPException (come tmdb_client).
"""
import re
import threading
import time
from typing import Any, Optional

import httpx
from fastapi import HTTPException

DEFAULT_TTL = 600  # 10 minuti: i cataloghi esterni cambiano di rado
_TAG_RE = re.compile(r"<[^>]+>")

# Cache: chiave -> (scadenza_epoch, dati). Protetta da lock perche' gli endpoint
# sync di FastAPI girano su un threadpool.
_cache: dict[str, tuple[float, Any]] = {}
_cache_lock = threading.Lock()

# Ultimo istante di chiamata per servizio, per il throttle.
_last_call: dict[str, float] = {}
_throttle_lock = threading.Lock()


def _key(url: str, params: Optional[dict], headers: Optional[dict]) -> str:
    items = sorted((params or {}).items())
    # Includiamo solo header che cambiano la risposta (es. api_key), non tutti.
    hdr = sorted((headers or {}).items())
    return f"{url}?{items}#{hdr}"


def _cache_get(key: str) -> Optional[Any]:
    with _cache_lock:
        entry = _cache.get(key)
        if entry is None:
            return None
        expires, data = entry
        if expires < time.time():
            _cache.pop(key, None)
            return None
        return data


def _cache_set(key: str, data: Any, ttl: int) -> None:
    with _cache_lock:
        _cache[key] = (time.time() + ttl, data)


def _throttle(service: str, min_interval: float) -> None:
    if min_interval <= 0:
        return
    with _throttle_lock:
        now = time.monotonic()
        last = _last_call.get(service, 0.0)
        wait = min_interval - (now - last)
        if wait > 0:
            time.sleep(wait)
        _last_call[service] = time.monotonic()


def get_json(
    url: str,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    *,
    service: str = "API esterna",
    timeout: float = 10.0,
    ttl: int = DEFAULT_TTL,
    min_interval: float = 0.0,
    not_found_ok: bool = False,
    retries: int = 1,
) -> Optional[dict[str, Any]]:
    """GET JSON con cache/throttle e un piccolo retry sui guasti transitori.

    Ritenta (fino a ``retries`` volte, con backoff breve) su timeout/errore di
    rete e su errori 5xx (Jikan e Comic Vine ogni tanto rispondono 502/504).
    In caso di 404 solleva HTTPException(404) o ritorna None se ``not_found_ok``.
    Il 429 (quota) NON viene ritentato: e' un limite, non un guasto."""
    key = _key(url, params, headers)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    response = None
    for attempt in range(retries + 1):
        _throttle(service, min_interval)
        try:
            response = httpx.get(
                url, params=params, headers=headers, timeout=timeout, follow_redirects=True
            )
        except httpx.RequestError as exc:
            if attempt < retries:
                time.sleep(0.6 * (attempt + 1))
                continue
            raise HTTPException(
                status_code=502, detail=f"Impossibile contattare {service}: {exc}"
            ) from exc

        # Guasto transitorio del server: ritenta se possibile.
        if response.status_code >= 500 and attempt < retries:
            time.sleep(0.6 * (attempt + 1))
            continue
        break

    if response.status_code == 404:
        if not_found_ok:
            return None
        raise HTTPException(status_code=404, detail=f"Risorsa non trovata su {service}.")
    if response.status_code == 429:
        raise HTTPException(
            status_code=503,
            detail=f"{service} ha applicato un limite di richieste. Riprova tra poco.",
        )
    if response.status_code >= 500:
        # Guasto a monte (es. Jikan quando MyAnimeList e' irraggiungibile).
        raise HTTPException(
            status_code=503,
            detail=f"{service} non risponde in questo momento. Riprova tra poco.",
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502, detail=f"Errore {service} ({response.status_code})."
        )

    data = response.json()
    _cache_set(key, data, ttl)
    return data


def post_json(
    url: str,
    json_body: dict,
    headers: Optional[dict] = None,
    *,
    service: str = "API esterna",
    timeout: float = 15.0,
    ttl: int = DEFAULT_TTL,
    min_interval: float = 0.0,
    retries: int = 1,
) -> dict[str, Any]:
    """POST JSON con cache/throttle/retry (per API GraphQL come AniList)."""
    key = _key(url, json_body, headers)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    response = None
    for attempt in range(retries + 1):
        _throttle(service, min_interval)
        try:
            response = httpx.post(url, json=json_body, headers=headers, timeout=timeout)
        except httpx.RequestError as exc:
            if attempt < retries:
                time.sleep(0.6 * (attempt + 1))
                continue
            raise HTTPException(
                status_code=502, detail=f"Impossibile contattare {service}: {exc}"
            ) from exc

        if response.status_code >= 500 and attempt < retries:
            time.sleep(0.6 * (attempt + 1))
            continue
        break

    if response.status_code == 429:
        raise HTTPException(
            status_code=503,
            detail=f"{service} ha applicato un limite di richieste. Riprova tra poco.",
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=503 if response.status_code >= 500 else 502,
            detail=f"{service} non risponde correttamente ({response.status_code}).",
        )

    data = response.json()
    if data.get("errors"):
        # GraphQL puo' rispondere 200 con un elenco di errori nel corpo.
        first = data["errors"][0].get("message", "errore sconosciuto")
        raise HTTPException(status_code=502, detail=f"Errore {service}: {first}")

    _cache_set(key, data, ttl)
    return data


def strip_html(value: Optional[str]) -> Optional[str]:
    """Rimuove tag HTML semplici (<br>, <i>, ...) da un testo, per le
    descrizioni di API che li includono anche quando richiesto testo puro."""
    if not value:
        return None
    import html

    text = html.unescape(_TAG_RE.sub(" ", value))
    text = re.sub(r"\s+", " ", text).strip()
    return text or None
