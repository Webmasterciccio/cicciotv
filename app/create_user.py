"""Crea (o aggiorna) un utente di accesso da riga di comando.

Uso, dalla cartella del progetto con il venv attivo:

    python -m app.create_user

Chiede nome e PIN (nascosto). Se il nome esiste gia', ne aggiorna il PIN.
Serve soprattutto per creare il PRIMO utente, quando ancora non si puo'
accedere dall'interfaccia.
"""
import getpass
import sys

from . import auth, models
from .database import Base, SessionLocal, engine


def main() -> None:
    Base.metadata.create_all(bind=engine)

    name = input("Nome utente (es. Ciccio): ").strip()
    if not name:
        print("Nome vuoto, annullato.")
        sys.exit(1)

    pin = getpass.getpass("PIN (min 4 cifre): ").strip()
    if len(pin) < 4:
        print("PIN troppo corto (minimo 4).")
        sys.exit(1)
    if pin != getpass.getpass("Ripeti il PIN: ").strip():
        print("I due PIN non coincidono.")
        sys.exit(1)

    db = SessionLocal()
    try:
        pin_hash, salt = auth.hash_pin(pin)
        existing = db.query(models.User).filter(models.User.name == name).first()
        if existing:
            existing.pin_hash, existing.pin_salt = pin_hash, salt
            action = "aggiornato"
        else:
            db.add(models.User(name=name, pin_hash=pin_hash, pin_salt=salt))
            action = "creato"
        db.commit()
        print(f"Utente '{name}' {action}. Ora puoi accedere con il PIN.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
