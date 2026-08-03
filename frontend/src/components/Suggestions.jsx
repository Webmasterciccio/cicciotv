import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { dismissSuggestion, getSuggestions, importItem } from '../api.js'
import MediaPreview from './MediaPreview.jsx'
import Poster from './Poster.jsx'
import { isRead } from '../mediaMeta.js'

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
  if (state === 'added') return 'Aggiunto ✓'
  if (state === 'exists') return 'Già in libreria'
  if (state === 'error') return 'Riprova'
  return 'Aggiungi'
}

// Griglia di titoli consigliati (motore ibrido: «perché hai visto/letto X» +
// generi/popolari), con filtri, «Mostra altri» e «non mi interessa».
function Suggestions({ title = 'Consigliati per te', mediaType = 'tv' }) {
  const [items, setItems] = useState(null)
  const [addState, setAddState] = useState({})
  const [preview, setPreview] = useState(null)
  const [loadingMore, setLoadingMore] = useState(false)
  const [sort, setSort] = useState('popularity')
  const [minRating, setMinRating] = useState('')
  const [period, setPeriod] = useState('')
  const [onlyIt, setOnlyIt] = useState(false)

  // La lingua originale ha senso solo per serie/film (TMDB); per gli altri tipi
  // i titoli sono in giapponese/inglese, quindi il filtro «Solo IT» non serve.
  const langFilterAvailable = mediaType === 'tv' || mediaType === 'movie'

  const buildOpts = useCallback(
    (exclude) => {
      const opts = { sort }
      if (minRating) opts.minRating = minRating
      if (period) {
        const now = new Date().getFullYear()
        opts.yearFrom = period === '2000' ? 2000 : now - Number(period)
      }
      if (onlyIt && langFilterAvailable) opts.lang = 'it'
      if (exclude) opts.exclude = exclude
      return opts
    },
    [sort, minRating, period, onlyIt, langFilterAvailable],
  )

  const load = useCallback(() => {
    setItems(null)
    setAddState({})
    getSuggestions(mediaType, buildOpts())
      .then(setItems)
      .catch(() => setItems([]))
  }, [mediaType, buildOpts])

  useEffect(() => {
    load()
  }, [load])

  async function loadMore() {
    if (!items) return
    setLoadingMore(true)
    try {
      const shown = items.map((i) => i.external_id)
      const more = await getSuggestions(mediaType, buildOpts(shown))
      setItems((prev) => [...prev, ...more])
    } catch {
      // in caso di errore lasciamo la lista com'è
    } finally {
      setLoadingMore(false)
    }
  }

  async function handleDismiss(item) {
    setItems((prev) => (prev ? prev.filter((i) => i.external_id !== item.external_id) : prev))
    try {
      await dismissSuggestion(item)
    } catch {
      // la rimozione locale è già avvenuta; ignoriamo l'errore di rete
    }
  }

  async function handleAdd(item) {
    setAddState((prev) => ({ ...prev, [item.external_id]: 'adding' }))
    try {
      await importItem(item, 'da_vedere')
      setAddState((prev) => ({ ...prev, [item.external_id]: 'added' }))
    } catch (err) {
      setAddState((prev) => ({
        ...prev,
        [item.external_id]: err.status === 409 ? 'exists' : 'error',
      }))
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
        {langFilterAvailable && (
          <label className="suggestions-lang">
            <input type="checkbox" checked={onlyIt} onChange={(e) => setOnlyIt(e.target.checked)} />
            Solo IT
          </label>
        )}
      </div>

      {items === null && <p className="hint">Caricamento consigli…</p>}

      {items !== null && items.length === 0 && (
        <p className="hint">
          Nessun consiglio con questi filtri. Prova ad allentarli
          {isRead(mediaType) ? '' : ', scegli i tuoi generi preferiti in '}
          {isRead(mediaType) ? '' : <Link to="/impostazioni">Impostazioni</Link>} e aggiungi
          qualche titolo alla libreria per avere consigli su misura.
        </p>
      )}

      {items !== null && items.length > 0 && (
        <>
          <div className="suggestions-grid">
            {items.map((item) => {
              const state = addState[item.external_id]
              return (
                <div key={`${item.source}-${item.external_id}`} className="suggestion-card">
                  <button
                    type="button"
                    className="suggestion-dismiss"
                    title="Non mi interessa"
                    aria-label="Non mi interessa"
                    onClick={() => handleDismiss(item)}
                  >
                    ✕
                  </button>
                  <button
                    type="button"
                    className="result-open"
                    onClick={() => setPreview(item)}
                    title="Vedi dettagli"
                    aria-label={`Dettagli di ${item.title}`}
                  >
                    <Poster url={item.poster_url} title={item.title} />
                  </button>
                  <div className="suggestion-body">
                    <button
                      type="button"
                      className="result-title suggestion-title"
                      onClick={() => setPreview(item)}
                    >
                      {item.title}
                    </button>
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

      {preview && (
        <MediaPreview
          item={preview}
          onClose={() => setPreview(null)}
          onAdded={(it) => setAddState((prev) => ({ ...prev, [it.external_id]: 'added' }))}
        />
      )}
    </section>
  )
}

export default Suggestions
