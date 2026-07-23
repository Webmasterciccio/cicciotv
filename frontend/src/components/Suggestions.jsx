import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { dismissSuggestion, getSuggestions, importFromTmdb } from '../api.js'
import Poster from './Poster.jsx'

const SORTS = [
  { value: 'popularity', label: 'Consigliati' },
  { value: 'rating', label: 'Voto più alto' },
  { value: 'recent', label: 'Più recenti' },
]
const RATINGS = [
  { value: '', label: 'Voto: tutti' },
  { value: '6', label: '★ 6+' },
  { value: '7', label: '★ 7+' },
  { value: '8', label: '★ 8+' },
]
const PERIODS = [
  { value: '', label: 'Periodo: tutto' },
  { value: '5', label: 'Ultimi 5 anni' },
  { value: '10', label: 'Ultimi 10 anni' },
  { value: '2000', label: 'Dal 2000' },
]

function addLabel(state) {
  if (state === 'adding') return 'Aggiungo…'
  if (state === 'added') return 'Aggiunta ✓'
  if (state === 'exists') return 'Già in libreria'
  if (state === 'error') return 'Riprova'
  return 'Aggiungi'
}

// Griglia di titoli consigliati (motore ibrido: «perché hai visto X» + generi),
// con filtri, «Mostra altri» e possibilità di scartare («non mi interessa»).
function Suggestions({ title = 'Consigliati per te', mediaType = 'tv' }) {
  const [items, setItems] = useState(null)
  const [addState, setAddState] = useState({})
  const [loadingMore, setLoadingMore] = useState(false)
  const [sort, setSort] = useState('popularity')
  const [minRating, setMinRating] = useState('')
  const [period, setPeriod] = useState('')
  const [onlyIt, setOnlyIt] = useState(false)

  const buildOpts = useCallback(
    (exclude) => {
      const opts = { sort }
      if (minRating) opts.minRating = minRating
      if (period) {
        const now = new Date().getFullYear()
        opts.yearFrom = period === '2000' ? 2000 : now - Number(period)
      }
      if (onlyIt) opts.lang = 'it'
      if (exclude) opts.exclude = exclude
      return opts
    },
    [sort, minRating, period, onlyIt],
  )

  const load = useCallback(() => {
    setItems(null)
    setAddState({})
    getSuggestions(mediaType, buildOpts())
      .then(setItems)
      .catch(() => setItems([]))
  }, [mediaType, buildOpts])

  // Ricarica quando cambia tipo o uno dei filtri.
  useEffect(() => {
    load()
  }, [load])

  async function loadMore() {
    if (!items) return
    setLoadingMore(true)
    try {
      const shown = items.map((i) => i.tmdb_id)
      const more = await getSuggestions(mediaType, buildOpts(shown))
      setItems((prev) => [...prev, ...more])
    } catch {
      // in caso di errore lasciamo la lista com'è
    } finally {
      setLoadingMore(false)
    }
  }

  async function handleDismiss(tmdbId) {
    setItems((prev) => (prev ? prev.filter((i) => i.tmdb_id !== tmdbId) : prev))
    try {
      await dismissSuggestion(tmdbId, mediaType)
    } catch {
      // la rimozione locale è già avvenuta; ignoriamo l'errore di rete
    }
  }

  async function handleAdd(tmdbId) {
    setAddState((prev) => ({ ...prev, [tmdbId]: 'adding' }))
    try {
      await importFromTmdb(tmdbId, 'da_vedere', mediaType)
      setAddState((prev) => ({ ...prev, [tmdbId]: 'added' }))
    } catch (err) {
      setAddState((prev) => ({ ...prev, [tmdbId]: err.status === 409 ? 'exists' : 'error' }))
    }
  }

  return (
    <section className="suggestions">
      <div className="suggestions-head">
        <h2>{title}</h2>
        <button type="button" className="link-button" onClick={load} title="Rigenera i consigli">
          ↻ Rigenera
        </button>
      </div>

      <div className="suggestions-controls">
        <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Ordina">
          {SORTS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select value={minRating} onChange={(e) => setMinRating(e.target.value)} aria-label="Voto minimo">
          {RATINGS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select value={period} onChange={(e) => setPeriod(e.target.value)} aria-label="Periodo">
          {PERIODS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <label className="suggestions-lang">
          <input type="checkbox" checked={onlyIt} onChange={(e) => setOnlyIt(e.target.checked)} />
          Solo IT
        </label>
      </div>

      {items === null && <p className="hint">Caricamento consigli…</p>}

      {items !== null && items.length === 0 && (
        <p className="hint">
          Nessun consiglio con questi filtri. Prova ad allentarli, oppure scegli i tuoi generi
          preferiti in <Link to="/impostazioni">Impostazioni</Link> e aggiungi qualche titolo alla
          libreria per avere consigli su misura.
        </p>
      )}

      {items !== null && items.length > 0 && (
        <>
          <div className="suggestions-grid">
            {items.map((item) => {
              const state = addState[item.tmdb_id]
              return (
                <div key={item.tmdb_id} className="suggestion-card">
                  <button
                    type="button"
                    className="suggestion-dismiss"
                    title="Non mi interessa"
                    aria-label="Non mi interessa"
                    onClick={() => handleDismiss(item.tmdb_id)}
                  >
                    ✕
                  </button>
                  <Poster url={item.poster_url} title={item.title} />
                  <div className="suggestion-body">
                    <h3 className="suggestion-title">{item.title}</h3>
                    {item.reason && <p className="suggestion-reason">{item.reason}</p>}
                    <p className="hint suggestion-meta">
                      {[
                        item.vote_average ? `★ ${item.vote_average.toFixed(1)}` : null,
                        item.first_air_date?.slice(0, 4),
                      ]
                        .filter(Boolean)
                        .join(' · ')}
                    </p>
                    <button
                      type="button"
                      className="suggestion-add"
                      onClick={() => handleAdd(item.tmdb_id)}
                      disabled={state === 'adding' || state === 'added' || state === 'exists'}
                    >
                      {addLabel(state)}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>

          <button
            type="button"
            className="suggestions-more"
            onClick={loadMore}
            disabled={loadingMore}
          >
            {loadingMore ? 'Carico…' : 'Mostra altri'}
          </button>
        </>
      )}
    </section>
  )
}

export default Suggestions
