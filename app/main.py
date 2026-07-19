"""Punto di avvio dell'applicazione FastAPI."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import series, tmdb

# Crea le tabelle nel database al primo avvio (se non esistono gia').
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CiccioTV",
    description="Backend per tenere traccia delle serie TV: da vedere, in corso, viste.",
    version="0.1.0",
)

# Il frontend gira su un dev server separato (Vite, porta 5173): serve CORS
# perche' e' un'origine diversa da quella del backend (porta 8000).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(series.router)
app.include_router(tmdb.router)


@app.get("/", tags=["health"])
def root():
    """Endpoint di controllo: conferma che il server e' attivo."""
    return {"app": "CiccioTV", "status": "ok", "docs": "/docs"}
