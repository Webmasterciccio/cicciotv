"""Endpoint di autenticazione: login, logout, stato e utente corrente."""
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status", response_model=schemas.AuthStatus)
def status(db: Session = Depends(get_db)):
    """Dice se esiste almeno un utente (per capire se serve la configurazione)."""
    exists = db.query(models.User.id).first() is not None
    return {"users_exist": exists}


@router.post("/setup", response_model=schemas.LoginResponse)
def setup(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    """Crea il PRIMO utente e logga subito. Consentito solo finche' non esiste
    ancora nessun utente: dopo, si aggiungono dall'app (endpoint /users, protetto)."""
    if db.query(models.User.id).first() is not None:
        raise HTTPException(status_code=403, detail="Configurazione gia' completata")
    pin_hash, salt = auth.hash_pin(payload.pin.strip())
    user = models.User(name=payload.name.strip(), pin_hash=pin_hash, pin_salt=salt)
    db.add(user)
    db.commit()
    db.refresh(user)
    sess = auth.create_session(db, user)
    return {"token": sess.token, "user": user}


@router.post("/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Accesso tramite PIN. Con PIN corretto emette un token di sessione."""
    ip = auth.client_ip(request)
    remaining = auth.lockout_remaining(ip)
    if remaining:
        raise HTTPException(
            status_code=429,
            detail=f"Troppi tentativi. Riprova tra {remaining} secondi.",
        )

    pin = payload.pin.strip()
    for user in db.query(models.User).all():
        if auth.verify_pin(pin, user.pin_hash, user.pin_salt):
            auth.reset_failures(ip)
            sess = auth.create_session(db, user)
            return {"token": sess.token, "user": user}

    auth.record_failure(ip)
    raise HTTPException(status_code=401, detail="PIN errato")


@router.post("/logout", status_code=204)
def logout(authorization: str = Header(default=""), db: Session = Depends(get_db)):
    """Invalida il token corrente (pulsante 'Esci')."""
    auth.delete_session(db, authorization)
    return None


@router.get("/me", response_model=schemas.UserRead)
def me(user: models.User = Depends(auth.get_current_user)):
    """Chi sono: usato dal frontend per validare il token salvato all'avvio."""
    return user
