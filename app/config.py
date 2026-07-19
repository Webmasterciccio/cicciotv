"""Configurazione dell'applicazione, caricata da variabili d'ambiente / file .env."""
import os

from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_LANGUAGE = os.getenv("TMDB_LANGUAGE", "it-IT")
