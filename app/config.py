"""Configurazione dell'applicazione, caricata da variabili d'ambiente / file .env."""
import os

from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_LANGUAGE = os.getenv("TMDB_LANGUAGE", "it-IT")
# Regione usata per sapere su quali servizi e' disponibile una serie ("dove vederla").
TMDB_REGION = os.getenv("TMDB_REGION", "IT")

# Fumetti occidentali (Comic Vine): chiave obbligatoria e gratuita, ottenibile da
# https://comicvine.gamespot.com/api/ dopo la registrazione. Va solo in .env.
COMICVINE_API_KEY = os.getenv("COMICVINE_API_KEY")

# Libri (Google Books): la chiave e' opzionale (alza le quote). Senza chiave
# l'API funziona comunque, con limiti per IP.
GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")
