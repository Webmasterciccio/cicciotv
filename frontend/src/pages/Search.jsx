import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getLibraryIds, importItem, searchCatalog } from '../api.js'
import MediaPreview from '../components/MediaPreview.jsx'
import Poster from '../components/Poster.jsx'
import Suggestions from '../components/Suggestions.jsx'
import {
  langFilterAvailable,
  MEDIA_TYPES,
  PERIOD_OPTIONS,
  RATING_OPTIONS,
  searchPlaceholder,
  suggestionsTitle,
} from '../mediaMeta.js'

// Fonti "extra" (oltre a quella primaria del tipo) da segnalare sulla card,
// cosi' si vede quali risultati "tv" vengono dalla fusione con AniList.
const SOURCE_LABEL = { anilist: 'AniList' }

function addLabel(state) {
  if (state === 'adding') return 'Aggiungo…'
  if (state === 'added') return 'Aggiunto ✓'
  if (state === 'exists') return '✓ Già in libreria'
  if (state === 'error') return 'Riprova'
  return 'Aggiungi'
}

function Search() {
  const navigate = useNavigate()
  const [mediaType, setMediaType] = useState('tv')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState(null)
  const [addState, setAddState] = useState({}) // external_id -> stato
  const [libraryIds, setLibraryIds] = useState(new Set()) // external_id gia' in libreria per questo tipo
  const [preview, setPreview] = useState(null) // item mostrato in anteprima
  const [minRating, setMinRating] = useState('')
  const [period, setPeriod] = useState('')
  const [onlyIt, setOnlyIt] = useState(false)

  const showLangFilter = langFilterAvailable(mediaType)

  // Carichiamo gli id gia' in libreria per questo tipo, cosi' i risultati di
  // ricerca possono mostrare subito "gia' in libreria" senza dover cliccare.
  useEffect(() => {
    let alive = true
    getLibraryIds(mediaType)
      .then((ids) => alive && setLibraryIds(new Set(ids)))
      .catch(() => alive && setLibraryIds(new Set()))
    return () => {
      alive = false
    }
  }, [mediaType])

  // overrides permette di applicare un filtro appena cambiato prima che lo
  // stato React si aggiorni (onChange passa il nuovo valore direttamente).
  function buildOpts(pageNum, overrides = {}) {
    const rating = 'minRating' in overrides ? overrides.minRating : minRating
    const per = 'period' in overrides ? overrides.period : period
    const it = 'onlyIt' in overrides ? overrides.onlyIt : onlyIt
    const opts = { page: pageNum }
    if (rating) opts.minRating = rating
    if (per) {
      const now = new Date().getFullYear()
      opts.yearFrom = per === '2000' ? 2000 : now - Number(per)
    }
    if (it && showLangFilter) opts.lang = 'it'
    return opts
  }

  async function runSearch(pageNum, overrides = {}) {
    const q = query.trim()
    if (!q) return
    if (pageNum === 1) {
      setLoading(true)
      setError(null)
    } else {
      setLoadingMore(true)
    }
    try {
      const data = await searchCatalog(q, mediaType, buildOpts(pageNum, overrides))
      setResults((prev) => (pageNum === 1 ? data : [...(prev || []), ...data]))
      setPage(pageNum)
      if (pageNum === 1) {
        const initial = {}
        data.forEach((item) => {
          if (libraryIds.has(String(item.external_id))) initial[item.external_id] = 'exists'
        })
        setAddState(initial)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    runSearch(1)
  }

  // Cambiare un filtro con una ricerca gia' attiva la rilancia subito.
  function handleFilterChange(overrides) {
    if ('minRating' in overrides) setMinRating(overrides.minRating)
    if ('period' in overrides) setPeriod(overrides.period)
    if ('onlyIt' in overrides) setOnlyIt(overrides.onlyIt)
    if (results !== null) runSearch(1, overrides)
  }

  function loadMore() {
    runSearch(page + 1)
  }

  function changeType(type) {
    setMediaType(type)
    setResults(null)
    setError(null)
  }

  function clearSearch() {
    setQuery('')
    setResults(null)
    setError(null)
  }

  async function handleAdd(item) {
    setAddState((prev) => ({ ...prev, [item.external_id]: 'adding' }))
    try {
      await importItem(item, 'da_vedere')
      setAddState((prev) => ({ ...prev, [item.external_id]: 'added' }))
      navigate('/')
    } catch (err) {
      setAddState((prev) => ({
        ...prev,
        [item.external_id]: err.status === 409 ? 'exists' : 'error',
      }))
    }
  }

  return (
    <div className="search-page">
      <div className="type-toggle type-toggle-scroll">
        {MEDIA_TYPES.map((m) => (
          <button
            key={m.type}
            type="button"
            className={mediaType === m.type ? 'on' : ''}
            onClick={() => changeType(m.type)}
          >
            {m.label}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="search-form">
        <input
          type="text"
          placeholder={searchPlaceholder(mediaType)}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Cerco…' : 'Cerca'}
        </button>
      </form>

      <div className="suggestions-controls">
        <select
          value={minRating}
          onChange={(e) => handleFilterChange({ minRating: e.target.value })}
          aria-label="Voto minimo"
        >
          {RATING_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={period}
          onChange={(e) => handleFilterChange({ period: e.target.value })}
          aria-label="Periodo"
        >
          {PERIOD_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        {showLangFilter && (
          <label className="suggestions-lang">
            <input
              type="checkbox"
              checked={onlyIt}
              onChange={(e) => handleFilterChange({ onlyIt: e.target.checked })}
            />
            Solo IT
          </label>
        )}
      </div>

      {error && <p className="error">Errore nella ricerca: {error}</p>}

      {/* Risultati di ricerca */}
      {results !== null && (
        <>
          <div className="results-header">
            <h2>Risultati</h2>
            <button type="button" className="link-button" onClick={clearSearch}>
              ← Torna ai consigli
            </button>
          </div>
          {results.length === 0 && <p className="hint">Nessun risultato.</p>}
          <div className="search-results">
            {results.map((item) => {
              const state = addState[item.external_id]
              const sourceTag = mediaType === 'tv' ? SOURCE_LABEL[item.source] : null
              const sub = [
                item.vote_average ? `★ ${item.vote_average.toFixed(1)}` : null,
                item.first_air_date?.slice(0, 4),
                (item.authors || [])[0],
                sourceTag,
              ]
                .filter(Boolean)
                .join(' · ')
              return (
                <div key={`${item.source}-${item.external_id}`} className="search-result">
                  <button
                    type="button"
                    className="result-open"
                    onClick={() => setPreview(item)}
                    title="Vedi dettagli"
                    aria-label={`Dettagli di ${item.title}`}
                  >
                    <Poster url={item.poster_url} title={item.title} />
                  </button>
                  <div className="search-result-body">
                    <button type="button" className="result-title" onClick={() => setPreview(item)}>
                      {item.title}
                    </button>
                    <p className="hint">{sub || 'Dati non disponibili'}</p>
                    <p className={`overview${item.overview ? '' : ' overview-empty'}`}>
                      {item.overview || 'Nessuna descrizione disponibile.'}
                    </p>
                    <button
                      type="button"
                      onClick={() => handleAdd(item)}
                      disabled={state === 'adding' || state === 'added' || state === 'exists'}
                    >
                      {addLabel(state)}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
          {results.length > 0 && (
            <button
              type="button"
              className="suggestions-more"
              onClick={loadMore}
              disabled={loadingMore}
            >
              {loadingMore ? 'Carico…' : 'Mostra altri'}
            </button>
          )}
        </>
      )}

      {/* Consigli (quando non stai cercando) */}
      {results === null && (
        <Suggestions mediaType={mediaType} title={suggestionsTitle(mediaType)} />
      )}

      {preview && (
        <MediaPreview
          item={preview}
          initialState={addState[preview.external_id] ?? null}
          onClose={() => setPreview(null)}
          onAdded={(it) => setAddState((prev) => ({ ...prev, [it.external_id]: 'added' }))}
        />
      )}
    </div>
  )
}

export default Search
