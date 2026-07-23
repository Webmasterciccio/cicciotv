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
            "user_id": "INTEGER",
        },
        "users": {
            "is_admin": "BOOLEAN DEFAULT 0",
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


def _migrate_multiuser() -> None:
    """Passaggio a multi-utente: promuove il primo utente ad admin e assegna a
    lui la libreria e le preferenze preesistenti (che prima erano condivise).
    Idempotente: si puo' rieseguire a ogni avvio senza effetti collaterali."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "users" not in tables:
        return
    with engine.begin() as conn:
        first = conn.execute(text("SELECT id FROM users ORDER BY id LIMIT 1")).fetchone()
        if not first:
            return  # nessun utente ancora: niente da assegnare
        admin_id = first[0]

        # Se nessuno e' admin, promuovi il primo utente creato.
        has_admin = conn.execute(text("SELECT 1 FROM users WHERE is_admin=1 LIMIT 1")).fetchone()
        if not has_admin:
            conn.execute(text("UPDATE users SET is_admin=1 WHERE id=:id"), {"id": admin_id})

        # Assegna all'admin le serie/film senza proprietario (libreria condivisa).
        if "series" in tables:
            conn.execute(
                text("UPDATE series SET user_id=:id WHERE user_id IS NULL"), {"id": admin_id}
            )

        # Copia le vecchie preferenze globali nelle impostazioni per-utente dell'admin.
        if "settings" in tables and "user_settings" in tables:
            already = conn.execute(text("SELECT 1 FROM user_settings LIMIT 1")).fetchone()
            if not already:
                rows = conn.execute(text("SELECT key, value FROM settings")).fetchall()
                for key, value in rows:
                    conn.execute(
                        text(
                            "INSERT INTO user_settings (user_id, key, value) "
                            "VALUES (:u, :k, :v)"
                        ),
                        {"u": admin_id, "k": key, "v": value},
                    )


_add_missing_columns()
_migrate_multiuser()

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
