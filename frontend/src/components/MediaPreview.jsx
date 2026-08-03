import { useEffect, useState } from 'react'
import { getCatalogDetails, getCatalogWatchProviders, importItem } from '../api.js'
import Poster from './Poster.jsx'
import { labelOf, unitLabel } from '../mediaMeta.js'

// Etichette leggibili per le categorie di servizi restituite da TMDB.
const PROVIDER_KIND_LABELS = {
  flatrate: 'Abbonamento',
  free: 'Gratis',
  ads: 'Con pubblicità',
  rent: 'Noleggio',
  buy: 'Acquisto',
}

function addLabel(state) {
  if (state === 'adding') return 'Aggiungo…'
  if (state === 'added') return 'Aggiunto ✓'
  if (state === 'exists') return 'Già in libreria'
  if (state === 'error') return 'Riprova'
  return 'Aggiungi alla libreria'
}

// Anteprima di un titolo (di qualsiasi sorgente) prima di aggiungerlo: modale
// con trama, generi, dati specifici del tipo e il pulsante per aggiungere.
function MediaPreview({ item, onClose, onAdded }) {
  const [details, setDetails] = useState(null)
  const [providers, setProviders] = useState(null)
  const [error, setError] = useState(null)
  const [addState, setAddState] = useState(null)

  const type = item.media_type
  const isWatchable = type === 'tv' || type === 'movie'

  useEffect(() => {
    let alive = true
    setDetails(null)
    setProviders(null)
    setError(null)
    getCatalogDetails(item)
      .then((d) => alive && setDetails(d))
      .catch((e) => alive && setError(e.message))
    // "Dove vederla" solo per serie/film; non blocca la scheda in caso di errore.
    if (isWatchable) {
      getCatalogWatchProviders(item)
        .then((p) => alive && setProviders(p))
        .catch(() => {})
    }
    return () => {
      alive = false
    }
  }, [item, isWatchable])

  // Chiusura con Esc e blocco dello scroll di sfondo mentre è aperta.
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [onClose])

  async function add() {
    setAddState('adding')
    try {
      await importItem(item, 'da_vedere')
      setAddState('added')
      if (onAdded) onAdded(item)
    } catch (e) {
      setAddState(e.status === 409 ? 'exists' : 'error')
    }
  }

  const d = details || {}
  // Riga di metadati compatta (solo le voci disponibili).
  const meta = []
  const year = (d.first_air_date || item.first_air_date || '').slice(0, 4)
  if (year) meta.push(year)
  if (d.number_of_episodes) meta.push(`${d.number_of_episodes} ${unitLabel(type)}`)
  if (d.volumes) meta.push(`${d.volumes} volumi`)
  if (d.chapters) meta.push(`${d.chapters} capitoli`)
  if (d.page_count) meta.push(`${d.page_count} pagine`)
  if (d.episode_run_time) meta.push(`${d.episode_run_time} min`)

  const credit = d.studio || d.publisher || (d.authors || []).join(', ')
  const rating = d.vote_average ?? item.vote_average
  const overview = d.overview || item.overview

  return (
    <div className="preview-overlay" onClick={onClose} role="presentation">
      <div
        className="preview-card"
        role="dialog"
        aria-modal="true"
        aria-label={item.title}
        onClick={(e) => e.stopPropagation()}
      >
        <button type="button" className="preview-close" onClick={onClose} aria-label="Chiudi">
          ✕
        </button>

        <div className="preview-head">
          <Poster url={item.poster_url} title={item.title} />
          <div className="preview-head-info">
            <span className="preview-type">{labelOf(type)}</span>
            <h2 className="preview-title">{item.title}</h2>
            {meta.length > 0 && <p className="hint preview-meta">{meta.join(' · ')}</p>}
            {rating ? <p className="preview-rating">★ {Number(rating).toFixed(1)}</p> : null}
            {credit && <p className="hint">{credit}</p>}

            <button
              type="button"
              className="preview-add"
              onClick={add}
              disabled={addState === 'adding' || addState === 'added' || addState === 'exists'}
            >
              {addLabel(addState)}
            </button>
          </div>
        </div>

        {d.genres?.length > 0 && (
          <div className="genres preview-genres">
            {d.genres.map((g) => (
              <span key={g} className="genre-chip">
                {g}
              </span>
            ))}
          </div>
        )}

        {error && <p className="error">Impossibile caricare i dettagli: {error}</p>}
        {!details && !error && <p className="hint">Caricamento dettagli…</p>}

        {overview && (
          <div className="preview-overview">
            <p>{overview}</p>
          </div>
        )}

        {providers && Object.keys(providers.providers || {}).length > 0 && (
          <section className="preview-section watch-providers">
            <h3>Dove vederla</h3>
            <div className="provider-groups">
              {Object.entries(providers.providers).map(([kind, list]) => (
                <div key={kind} className="provider-group">
                  <span className="provider-kind">{PROVIDER_KIND_LABELS[kind] ?? kind}</span>
                  <div className="provider-logos">
                    {list.map((p) => (
                      <span key={p.name} className="provider-chip" title={p.name}>
                        {p.logo_url ? (
                          <img src={p.logo_url} alt={p.name} loading="lazy" />
                        ) : (
                          <span className="provider-name">{p.name}</span>
                        )}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {d.cast?.length > 0 && (
          <section className="preview-section cast-section">
            <h3>{type === 'comic' ? 'Personaggi' : 'Cast'}</h3>
            <div className="cast-row">
              {d.cast.map((p) => (
                <div key={`${p.name}-${p.character}`} className="cast-card">
                  {p.profile_url ? (
                    <img src={p.profile_url} alt={p.name} loading="lazy" className="cast-photo" />
                  ) : (
                    <div className="cast-photo cast-photo-empty" aria-hidden="true">
                      {p.name?.slice(0, 1)}
                    </div>
                  )}
                  <span className="cast-name">{p.name}</span>
                  {p.character && <span className="cast-character hint">{p.character}</span>}
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}

export default MediaPreview
