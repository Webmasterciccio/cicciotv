# CiccioTV

App personale per tenere traccia di quello che guardi e leggi: **serie TV**
(anime incluso), **film**, **manga**, **libri** e **fumetti**, con ricerca,
anteprima cliccabile prima di aggiungere, tracciamento episodi/numeri o
progresso capitoli/pagine, consigli personalizzati, statistiche e accesso
multi-utente via PIN.

Backend Python + FastAPI + SQLite, frontend React + Vite (anche come app
Android tramite Capacitor).

## Sorgenti dati per tipo

| Tipo | Sorgente | Chiave richiesta | Tracciamento |
|------|----------|-------------------|--------------|
| Serie TV *(anime incluso)* | [TMDB](https://www.themoviedb.org/); se il titolo non è su TMDB (tipico di anime recenti/di nicchia) la ricerca ripiega automaticamente su [AniList](https://anilist.co/) | TMDB sì (gratuita) | lista episodi |
| Film | TMDB | TMDB sì | singolo |
| Manga | AniList | no | progresso capitoli/volumi |
| Libri | [Google Books](https://developers.google.com/books) | opzionale (alza le quote) | progresso pagine |
| Fumetti occidentali | [Comic Vine](https://comicvine.gamespot.com/api/) | sì (gratuita) | lista numeri |

Per ogni titolo, prima di aggiungerlo, puoi aprire un'**anteprima** con trama,
generi, cast e "dove vederla" (serie/film TMDB).

## Requisiti

- Python 3.11 o superiore
- Node.js 18 o superiore

## Installazione (una volta sola)

```powershell
# Dalla cartella del progetto
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configurazione delle sorgenti esterne

```powershell
Copy-Item .env.example .env
```

Poi apri `.env` e imposta le chiavi che ti servono:

- **`TMDB_API_KEY`** (consigliata): serve per Serie TV e Film. Crea un account
  gratuito su https://www.themoviedb.org/signup, genera una API key su
  https://www.themoviedb.org/settings/api (tipo "Developer", uso personale) e
  usa la **"API Key (v3 auth)"**.
- **`COMICVINE_API_KEY`** (serve solo per i Fumetti): registrati su
  https://comicvine.gamespot.com e copia la chiave da
  https://comicvine.gamespot.com/api/.
- **`GOOGLE_BOOKS_API_KEY`** (opzionale): senza chiave i Libri funzionano
  comunque, con un limite di richieste per IP più basso.
- Anime/manga (AniList) **non richiedono alcuna chiave**.

Senza `TMDB_API_KEY`/`COMICVINE_API_KEY` l'app funziona comunque: solo la
ricerca/import del tipo corrispondente risponderà con un errore chiaro finché
non imposti la chiave.

## Avvio del server

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Il server parte su **http://127.0.0.1:8000**.

- Documentazione interattiva (provi le API dal browser): **http://127.0.0.1:8000/docs**
- Il database `cicciotv.db` viene creato automaticamente al primo avvio.

Per usare l'app **dal telefono Android** (vedi sezione dedicata piu' sotto) il
server deve accettare connessioni dalla rete locale, non solo dal PC stesso:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> Al primo avvio in questa modalita' Windows potrebbe mostrare un prompt del
> Firewall Defender ("Consenti a Python di comunicare su reti private/pubbliche"):
> va accettato, altrimenti il telefono non riuscira' a raggiungere il server.

## Primo accesso (login con PIN)

L'app richiede un accesso con **PIN** (niente password in chiaro: solo hash
PBKDF2). Al primissimo avvio, se il database non ha ancora nessun utente,
appare un form "crea il tuo accesso" (nome + PIN): quel primo utente diventa
**amministratore** e può creare altri utenti da Impostazioni → Utenti. Ogni
utente ha la propria libreria, preferenze e statistiche separate.

## Frontend (installazione e avvio)

Installazione (una volta sola):
```powershell
cd frontend
npm install
```

Avvio (backend e frontend sono due processi separati, vanno avviati entrambi):
```powershell
# Terminale 1, dalla cartella del progetto
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload

# Terminale 2
cd frontend
npm run dev
```

Apri **http://localhost:5173** nel browser.

> Nota: usa `localhost`, non `127.0.0.1` — il server di sviluppo Vite in questo
> ambiente risponde solo sull'hostname `localhost`.

Pagine disponibili:
- **Libreria** (`/`) — libreria per tipo (Serie TV, Film, Manga, Libri,
  Fumetti), con le sezioni di stato adeguate (da vedere/leggere, in corso, visto/letto)
- **Cerca** (`/cerca`) — cerca ed esplora i consigli per tipo, con anteprima
  cliccabile prima di aggiungere un titolo
- **Dettaglio** (`/serie/{id}`) — trama, cast, dove vederla, generi; cambia
  stato/voto; spunta episodi/numeri visti oppure aggiorna il progresso
  capitoli/pagine (lo stato si aggiorna da solo)
- **Statistiche** (`/statistiche`) — riepilogo per tipo, episodi visti nel
  tempo, abitudini di visione
- **Impostazioni** (`/impostazioni`) — generi preferiti per tipo (usati dai
  consigli) e, per l'admin, gestione utenti

## App Android

L'app Android e' lo stesso frontend React impacchettato con
[Capacitor](https://capacitorjs.com/) in un guscio nativo (WebView). Il
codice dell'interfaccia e' identico a quello del sito: cambia solo l'indirizzo
del backend (`frontend/.env`), configurabile per puntare al PC in rete locale
oppure al dominio di produzione (vedi `DEPLOY.md`).

### Requisiti
- [Android Studio](https://developer.android.com/studio) (include Java/Android SDK)
- Telefono e PC sulla **stessa rete Wi-Fi** (per l'uso in sviluppo locale)

### Configurazione IP (sviluppo locale, da rifare se cambia la rete)

`frontend/.env` contiene l'indirizzo usato dall'app per raggiungere il
backend:

```
VITE_API_BASE_URL=http://<IP-DEL-TUO-PC>:8000
```

Trovi l'IP attuale con `ipconfig` (campo "Indirizzo IPv4" della rete attiva).

### Build dell'APK

Dopo ogni modifica al frontend o all'indirizzo del backend:

```powershell
cd frontend
npm run build
npx cap sync android
```

Poi, con Android Studio installato, o direttamente da riga di comando:

```powershell
cd android
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
.\gradlew.bat assembleDebug
```

L'APK generato si trova in `android/app/build/outputs/apk/debug/app-debug.apk`
e va copiato sul telefono (oppure, in Android Studio, lanciato direttamente
con il tasto ▶ Run, con debug USB attivo).

### Prima di usarla
1. Avvia il backend (in locale con `--host 0.0.0.0`, oppure verifica che il
   deploy di produzione sia attivo — deve restare acceso).
2. Accetta l'eventuale prompt del Firewall di Windows al primo avvio locale.
3. Apri l'app sul telefono: chiede il PIN come il sito.

## Deploy in produzione

Il progetto include una guida completa per pubblicarlo su un dominio HTTPS
pubblico (VM Ubuntu + Caddy come reverse proxy + backend come servizio
systemd): vedi **[`DEPLOY.md`](./DEPLOY.md)**.

## Endpoint principali

| Metodo | Percorso | Descrizione |
|--------|----------|-------------|
| GET    | `/` | Controllo stato server (pubblico) |
| GET/POST | `/auth/status`, `/auth/setup`, `/auth/login`, `/auth/logout`, `/auth/me` | Autenticazione via PIN |
| GET/POST/PATCH/DELETE | `/users` | Gestione utenti (solo admin) |
| POST   | `/series` | Aggiungi una serie/film/manga/libro/fumetto |
| GET    | `/series` | Elenca la libreria dell'utente (filtro `?status=`) |
| GET/PATCH/DELETE | `/series/{id}` | Dettaglio/aggiornamento/rimozione |
| GET    | `/series/{id}/details` | Info estese dalla sorgente (trama, cast, generi, autori...) |
| GET    | `/series/{id}/recommendations` | Titoli consigliati a partire da questo |
| GET    | `/series/{id}/watch-providers` | "Dove vederla" (solo TMDB) |
| GET    | `/series/{id}/episodes` | Episodi/numeri con stato visto/non visto |
| POST   | `/series/{id}/episodes/sync` | (Ri)scarica episodi/numeri dalla sorgente |
| PATCH  | `/series/{id}/episodes/{episode_id}` | Segna un episodio/numero visto/non visto |
| PATCH  | `/series/{id}/seasons/{n}` | Segna un'intera stagione vista/non vista |
| GET    | `/catalog/search` | Cerca sulla sorgente giusta per il tipo (`?query=&type=`) |
| GET    | `/catalog/genres` | Generi selezionabili per tipo |
| GET    | `/catalog/details`, `/catalog/watch-providers` | Anteprima di un titolo non ancora in libreria |
| GET    | `/catalog/suggestions` | Consigli personalizzati per tipo |
| POST   | `/catalog/suggestions/dismiss` | Scarta un consiglio ("non mi interessa") |
| POST   | `/catalog/import` | Importa un titolo trovato nella libreria |
| GET/PUT | `/settings` | Generi preferiti per tipo (per i consigli) |
| GET    | `/stats` | Statistiche della libreria dell'utente |

Documentazione interattiva completa (schema di richieste/risposte, provale dal
browser): **`/docs`**.

### Stati possibili
`da_vedere` · `in_corso` · `vista`

Quando sposti un titolo a `in_corso` viene registrata `started_at`; quando lo
sposti a `vista` viene registrata `finished_at`. Entrambe in automatico (anche
segnando episodi/numeri visti o aggiornando il progresso capitoli/pagine).

## Struttura del progetto

```
cicciotv/
├── app/
│   ├── main.py             # avvio FastAPI + registrazione router + migrazioni DB
│   ├── database.py         # connessione SQLite
│   ├── models.py           # tabelle (SQLAlchemy): Series, Episode, User, ...
│   ├── schemas.py          # validazione input/output (Pydantic)
│   ├── crud.py             # logica di accesso ai dati + stato automatico + statistiche
│   ├── auth.py             # hash PIN, sessioni, rate limiting login
│   ├── config.py           # variabili d'ambiente (.env)
│   ├── catalog.py          # dispatcher multi-sorgente: instrada per tipo e normalizza
│   ├── tmdb_client.py      # client HTTP verso TMDB (serie/film)
│   ├── anilist_client.py   # client GraphQL verso AniList (anime fallback/manga)
│   ├── jikan_client.py     # client verso Jikan (retrocompatibilita' sorgenti legacy)
│   ├── googlebooks_client.py  # client verso Google Books (libri)
│   ├── comicvine_client.py    # client verso Comic Vine (fumetti)
│   ├── http_util.py        # cache/throttle/retry condivisi tra i client HTTP
│   └── routers/
│       ├── auth.py         # /auth (login/logout/setup)
│       ├── users.py        # /users (gestione utenti, solo admin)
│       ├── series.py       # /series (libreria, episodi/numeri, dettagli)
│       ├── catalog.py      # /catalog (ricerca, generi, consigli, import)
│       ├── settings.py     # /settings (generi preferiti)
│       └── stats.py        # /stats (statistiche)
├── frontend/
│   ├── src/
│   │   ├── api.js            # chiamate al backend (URL da VITE_API_BASE_URL)
│   │   ├── auth.jsx          # contesto di autenticazione (token, utente corrente)
│   │   ├── mediaMeta.js      # etichette/verbi/comportamenti UI per tipo di media
│   │   ├── App.jsx           # routing (react-router-dom)
│   │   ├── components/       # Nav, SeriesCard, Poster, MediaPreview, Suggestions, ...
│   │   └── pages/             # Login, Dashboard, Search, SeriesDetail, Stats, Settings
│   ├── android/               # progetto nativo Android (Capacitor)
│   ├── capacitor.config.json  # config app Android (appId, cleartext HTTP)
│   ├── .env                   # indirizzo del backend (non versionato)
│   └── package.json
├── deploy/               # Caddyfile + unit systemd per il deploy in produzione
├── requirements.txt
├── .env.example          # modello per le chiavi delle API esterne (copiare in .env)
├── DEPLOY.md              # guida al deploy su VM con dominio HTTPS
└── cicciotv.db            # creato automaticamente al primo avvio
```
