"""Punto di avvio dell'applicazione FastAPI."""
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from . import auth
from .database import Base, engine
from .routers import auth as auth_router
from .routers import series, settings, stats, tmdb, users

# Crea le tabelle nel database al primo avvio (se non esistono gia').
Base.metadata.create_all(bind=engine)


def _add_missing_columns() -> None:
    """Migrazione leggera e additiva: aggiunge le colonne nuove alle tabelle
    esistenti senza cancellare i dati gia' presenti (SQLite ADD COLUMN)."""
    # Colonne introdotte dopo la prima versione: tabella -> {nome: tipo SQL}.
    new_columns = {
        "episodes": {
            "overview": "TEXT",
            "still_url": "VARCHAR",
            "air_date": "VARCHAR",
            "vote_average": "FLOAT",
            "runtime": "INTEGER",
        },
        "series": {
            "media_type": "VARCHAR DEFAULT 'tv'",
            "runtime": "INTEGER",
            "watch_location": "VARCHAR",
            "genres": "TEXT",
        },
    }
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, columns in new_columns.items():
            if table not in tables:
                continue
            existing = {col["name"] for col in inspector.get_columns(table)}
            for name, sql_type in columns.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"))


_add_missing_columns()

app = FastAPI(
    title="CiccioTV",
    description="Backend per tenere traccia delle serie TV: da vedere, in corso, viste.",
    version="0.1.0",
)

# CORS aperto a qualunque origine: l'autenticazione avviene via token nell'header
# Authorization (non cookie), quindi non servono credenziali cross-origin. Cosi'
# evitiamo di indovinare l'esatta origine del WebView di Capacitor.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# L'autenticazione (login/logout) e' pubblica; tutto il resto richiede un token
# valido, applicato una volta sola qui come dependency del router.
protected = [Depends(auth.get_current_user)]

app.include_router(auth_router.router)
app.include_router(users.router)
app.include_router(series.router, dependencies=protected)
app.include_router(tmdb.router, dependencies=protected)
app.include_router(settings.router, dependencies=protected)
app.include_router(stats.router, dependencies=protected)


@app.get("/", tags=["health"])
def root():
    """Endpoint di controllo: conferma che il server e' attivo (nessun login)."""
    return {"app": "CiccioTV", "status": "ok", "docs": "/docs"}
