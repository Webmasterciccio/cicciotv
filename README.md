# CiccioTV

App per tenere traccia delle serie TV: **da vedere**, **in corso**, **viste**, con
ricerca e import da TMDB e tracciamento dei singoli episodi visti.
Progetto locale personale: backend Python + FastAPI + SQLite, frontend React + Vite.

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

## Configurazione TMDB (opzionale, per importare serie automaticamente)

1. Crea un account gratuito su https://www.themoviedb.org/signup
2. Genera una API key su https://www.themoviedb.org/settings/api (tipo "Developer", uso personale). Ti servirà la **"API Key (v3 auth)"**.
3. Copia `.env.example` in `.env` e incolla la chiave:

```powershell
Copy-Item .env.example .env
```

```
TMDB_API_KEY=la_tua_chiave_qui
```

Senza questa configurazione l'app funziona comunque normalmente: solo gli
endpoint `/tmdb/*` risponderanno con un errore chiaro finche' non imposti la chiave.

## Avvio del server

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Il server parte su **http://127.0.0.1:8000**.

- Documentazione interattiva (provi le API dal browser): **http://127.0.0.1:8000/docs**
- Il database `cicciotv.db` viene creato automaticamente al primo avvio.

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
- **Libreria** (`/`) — tre sezioni: In corso, Da vedere, Viste
- **Cerca** (`/cerca`) — cerca su TMDB e aggiungi una serie con un click
- **Dettaglio serie** (`/serie/{id}`) — cambia stato/voto, spunta gli episodi visti
  (lo stato della serie si aggiorna da solo: si sposta automaticamente su "in corso"
  al primo episodio visto e su "vista" quando li hai visti tutti)

## Endpoint

| Metodo | Percorso           | Descrizione                                  |
|--------|--------------------|----------------------------------------------|
| GET    | `/`                | Controllo stato server                       |
| POST   | `/series`          | Aggiungi una serie                           |
| GET    | `/series`          | Elenca le serie (filtro `?status=`)          |
| GET    | `/series/{id}`     | Dettaglio di una serie                       |
| PATCH  | `/series/{id}`     | Aggiorna campi (stato, voto, episodio, ...)  |
| DELETE | `/series/{id}`     | Rimuovi una serie                            |
| GET    | `/tmdb/search`     | Cerca serie su TMDB (`?query=`)              |
| POST   | `/tmdb/import/{tmdb_id}` | Importa una serie da TMDB nella libreria (`?status=`), sincronizza subito gli episodi |
| GET    | `/series/{id}/episodes` | Elenca gli episodi con stato visto/non visto |
| POST   | `/series/{id}/episodes/sync` | (Ri)scarica gli episodi da TMDB, preservando quelli gia' segnati visti |
| PATCH  | `/series/{id}/episodes/{episode_id}` | Segna un episodio visto/non visto (`{"watched": true}`) |
| PATCH  | `/series/{id}/seasons/{n}` | Segna un'intera stagione vista/non vista (`{"watched": true}`) |

### Stati possibili
`da_vedere` · `in_corso` · `vista`

Quando sposti una serie a `in_corso` viene registrata `started_at`; quando la
sposti a `vista` viene registrata `finished_at`. Entrambe in automatico.

## Esempi di chiamate (PowerShell)

Aggiungere una serie da vedere:
```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/series -Method Post -ContentType 'application/json' -Body '{"title":"Breaking Bad","status":"da_vedere","total_seasons":5}'
```

Elencare solo quelle in corso:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/series?status=in_corso"
```

Aggiornare stato e progresso (id 1):
```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/series/1 -Method Patch -ContentType 'application/json' -Body '{"status":"in_corso","current_season":1,"current_episode":3}'
```

Assegnare un voto quando finita:
```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/series/1 -Method Patch -ContentType 'application/json' -Body '{"status":"vista","rating":9}'
```

Eliminare (id 1):
```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/series/1 -Method Delete
```

Cercare una serie su TMDB:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/tmdb/search?query=Breaking%20Bad"
```

Importare una serie trovata (usando il suo `tmdb_id` restituito dalla ricerca):
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/tmdb/import/1396?status=da_vedere" -Method Post
```

## Struttura del progetto

```
cicciotv/
├── app/
│   ├── main.py          # avvio FastAPI + registrazione router + CORS
│   ├── database.py      # connessione SQLite
│   ├── models.py        # tabelle (SQLAlchemy): Series, Episode
│   ├── schemas.py       # validazione input/output (Pydantic)
│   ├── crud.py          # logica di accesso ai dati + stato automatico
│   ├── config.py        # variabili d'ambiente (.env)
│   ├── tmdb_client.py   # client HTTP verso le API di TMDB
│   └── routers/
│       ├── series.py    # endpoint /series + episodi/stagioni
│       └── tmdb.py      # endpoint /tmdb (ricerca e import)
├── frontend/
│   ├── src/
│   │   ├── api.js               # chiamate al backend
│   │   ├── App.jsx               # routing (react-router-dom)
│   │   ├── components/           # Nav, SeriesCard, Poster
│   │   └── pages/                # Dashboard, Search, SeriesDetail
│   └── package.json
├── requirements.txt
├── .env.example         # modello per la chiave TMDB (copiare in .env)
└── cicciotv.db          # creato automaticamente al primo avvio
```
