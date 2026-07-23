"""Gestione degli utenti (protetta): elenco, creazione, modifica PIN, rimozione."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db

# Solo l'amministratore puo' elencare/creare/modificare/eliminare utenti.
router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(auth.require_admin)],
)


@router.get("", response_model=list[schemas.UserRead])
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).order_by(models.User.name).all()


@router.post("", response_model=schemas.UserRead, status_code=201)
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    pin_hash, salt = auth.hash_pin(payload.pin.strip())
    user = models.User(name=payload.name.strip(), pin_hash=pin_hash, pin_salt=salt)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=schemas.UserRead)
def update_user(user_id: int, payload: schemas.UserUpdate, db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.pin is not None:
        user.pin_hash, user.pin_salt = auth.hash_pin(payload.pin.strip())
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    # Non lasciare l'app senza nessun accesso possibile.
    if db.query(models.User).count() <= 1:
        raise HTTPException(status_code=400, detail="Non puoi eliminare l'ultimo utente")
    # Rimuovi anche le sue sessioni attive.
    db.query(models.AuthSession).filter(models.AuthSession.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    return None
