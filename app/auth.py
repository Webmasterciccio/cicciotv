"""Autenticazione con PIN + token di sessione.

Il PIN e' salvato solo come hash PBKDF2 (con sale casuale per utente); al login
si emette un token opaco memorizzato nella tabella auth_sessions, con scadenza.
Un semplice rate limiting in memoria blocca i tentativi ripetuti (anti brute-force).
"""
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session as DbSession

from . import models
from .database import get_db

# Durata della sessione: dopo tanti giorni serve rifare il login.
SESSION_DAYS = 2
_PBKDF2_ROUNDS = 200_000

# Rate limiting in memoria per IP: dopo _MAX_ATTEMPTS PIN sbagliati si blocca
# per _LOCKOUT_SECONDS. Sufficiente contro il brute-force di un PIN a 6 cifre.
_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 300
_attempts: dict[str, list] = {}  # ip -> [tentativi_falliti, blocco_fino_a_epoch]


def hash_pin(pin: str, salt: str | None = None) -> tuple[str, str]:
    """Ritorna (hash_hex, salt_hex). Se salt e' None ne genera uno nuovo."""
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), _PBKDF2_ROUNDS)
    return dk.hex(), salt


def verify_pin(pin: str, pin_hash: str, salt: str) -> bool:
    calc, _ = hash_pin(pin, salt)
    return hmac.compare_digest(calc, pin_hash)


def client_ip(request: Request) -> str:
    """IP reale del client, tenendo conto del reverse proxy (Caddy imposta
    X-Forwarded-For). Serve al rate limiting per-IP."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "?"


def lockout_remaining(ip: str) -> int:
    """Secondi di blocco rimanenti per questo IP (0 se non bloccato)."""
    rec = _attempts.get(ip)
    if not rec:
        return 0
    _count, until = rec
    if until and time.time() < until:
        return int(until - time.time())
    return 0


def record_failure(ip: str) -> None:
    count, until = _attempts.get(ip, (0, 0))
    count += 1
    if count >= _MAX_ATTEMPTS:
        until = time.time() + _LOCKOUT_SECONDS
        count = 0
    _attempts[ip] = [count, until]


def reset_failures(ip: str) -> None:
    _attempts.pop(ip, None)


def create_session(db: DbSession, user: models.User) -> models.AuthSession:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    sess = models.AuthSession(token=token, user_id=user.id, expires_at=expires)
    db.add(sess)
    db.commit()
    return sess


def _token_from_header(authorization: str) -> str:
    if not authorization:
        return ""
    return authorization.removeprefix("Bearer ").strip()


def delete_session(db: DbSession, authorization: str) -> None:
    token = _token_from_header(authorization)
    if not token:
        return
    sess = db.get(models.AuthSession, token)
    if sess is not None:
        db.delete(sess)
        db.commit()


def get_current_user(
    authorization: str = Header(default=""),
    db: DbSession = Depends(get_db),
) -> models.User:
    """Dependency che protegge gli endpoint: richiede un token valido."""
    token = _token_from_header(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Non autenticato")
    sess = db.get(models.AuthSession, token)
    if sess is None:
        raise HTTPException(status_code=401, detail="Sessione non valida")
    expires = sess.expires_at
    if expires.tzinfo is None:  # SQLite restituisce datetime senza fuso
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        db.delete(sess)
        db.commit()
        raise HTTPException(status_code=401, detail="Sessione scaduta")
    user = db.get(models.User, sess.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Utente inesistente")
    return user


def require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    """Come get_current_user, ma consente solo agli amministratori."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Riservato all'amministratore")
    return user
