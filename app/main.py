"""Punto di avvio dell'applicazione FastAPI."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from .database import Base, engine
from .routers import series, settings, stats, tmdb

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

# App solo per uso personale, nessun dato sensibile/login: CORS aperto a
# qualunque origine per evitare di dover indovinare l'esatta origine usata
# dal WebView di Capacitor (che varia tra versioni/piattaforme).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(series.router)
app.include_router(tmdb.router)
app.include_router(settings.router)
app.include_router(stats.router)


@app.get("/", tags=["health"])
def root():
    """Endpoint di controllo: conferma che il server e' attivo."""
    return {"app": "CiccioTV", "status": "ok", "docs": "/docs"}
