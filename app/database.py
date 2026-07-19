"""Configurazione della connessione al database SQLite."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Il database e' un singolo file nella cartella del progetto.
SQLALCHEMY_DATABASE_URL = "sqlite:///./cicciotv.db"

# check_same_thread=False e' richiesto da SQLite quando usato con piu' thread
# (come fa il server web).
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Classe base da cui ereditano tutti i modelli/tabelle.
Base = declarative_base()


def get_db():
    """Dependency di FastAPI: fornisce una sessione DB e la chiude a fine richiesta."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
