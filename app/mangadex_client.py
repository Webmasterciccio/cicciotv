"""Client per MangaDex: copertine per singolo volume dei manga.

Ne' AniList ne' Jikan (le fonti usate per cercare/importare i manga) espongono
la copertina di ogni volume, solo il totale. MangaDex si' (endpoint /cover) ed
e' pubblica, senza chiave. Il collegamento con il titolo gia' in libreria (che
usa l'id AniList) avviene tramite ``links.al``, che MangaDex espone su ogni
scheda: niente matching "alla cieca" sul titolo, solo conferma dell'id.
Se il titolo non e' su MangaDex o non e' collegato, si torna lista vuota: il
manga resta comunque importabile, solo senza copertine per volume."""
from typing import Any, Optional

from . import http_util

URL = "https://api.mangadex.org"
SERVICE = "MangaDex"
COVERS_BASE = "https://uploads.mangadex.org/covers"


def _find_manga_id(title: str, anilist_id: str) -> Optional[str]:
    if not title:
        return None
    data = http_util.get_json(
        f"{URL}/manga",
        {"title": title, "limit": 20},
        service=SERVICE,
        min_interval=0.3,
        retries=1,
        not_found_ok=True,
    )
    if not data:
        return None
    for item in data.get("data") or []:
        links = (item.get("attributes") or {}).get("links") or {}
        if links.get("al") == str(anilist_id):
            return item.get("id")
    return None


def get_volumes(anilist_id: str, title: str) -> list[dict[str, Any]]:
    """Una unita' per volume (stesso formato delle altre fonti: season_number
    fisso a 1, episode_number = numero del volume, still_url = copertina)."""
    manga_id = _find_manga_id(title, anilist_id)
    if not manga_id:
        return []

    data = http_util.get_json(
        f"{URL}/cover",
        {"manga[]": manga_id, "limit": 100, "order[volume]": "asc"},
        service=SERVICE,
        min_interval=0.3,
        retries=1,
        not_found_ok=True,
    )
    if not data:
        return []

    units: list[dict[str, Any]] = []
    for cover in data.get("data") or []:
        attrs = cover.get("attributes") or {}
        file_name = attrs.get("fileName")
        if not file_name:
            continue
        try:
            volume_number = int(attrs.get("volume"))
        except (TypeError, ValueError):
            continue  # copertine senza volume (es. cover dell'intera serie)
        units.append(
            {
                "season_number": 1,
                "episode_number": volume_number,
                "name": f"Volume {volume_number}",
                "still_url": f"{COVERS_BASE}/{manga_id}/{file_name}.256.jpg",
            }
        )
    units.sort(key=lambda u: u["episode_number"])
    return units
