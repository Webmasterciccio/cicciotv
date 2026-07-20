import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getSuggestions, importFromTmdb } from '../api.js'
import Poster from './Poster.jsx'

function addLabel(state) {
  if (state === 'adding') return 'Aggiungo…'
  if (state === 'added') return 'Aggiunta ✓'
  if (state === 'exists') return 'Già in libreria'
  if (state === 'error') return 'Riprova'
  return 'Aggiungi'
}

// Griglia di serie consigliate in base ai generi preferiti (usata sia nella
// pagina Cerca sia nella libreria vuota).
function Suggestions({ title = 'Consigliati per te', mediaType = 'tv' }) {
  const [suggestions, setSuggestions] = useState(null)
  const [addState, setAddState] = useState({})

  useEffect(() => {
    setSuggestions(null)
    getSuggestions(20, mediaType)
      .then(setSuggestions)
      .catch(() => setSuggestions([]))
  }, [mediaType])

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
      <h2>{title}</h2>
      {suggestions === null && <p className="hint">Caricamento consigli…</p>}
      {suggestions !== null && suggestions.length === 0 && (
        <p className="hint">
          Nessun consiglio ancora. Scegli i tuoi generi preferiti in{' '}
          <Link to="/impostazioni">Impostazioni</Link> per ricevere suggerimenti sulla prossima
          serie da guardare.
        </p>
      )}
      {suggestions !== null && suggestions.length > 0 && (
        <div className="suggestions-grid">
          {suggestions.map((item) => {
            const state = addState[item.tmdb_id]
            return (
              <div key={item.tmdb_id} className="suggestion-card">
                <Poster url={item.poster_url} title={item.title} />
                <div className="suggestion-body">
                  <h3 className="suggestion-title">{item.title}</h3>
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
      )}
    </section>
  )
}

export default Suggestions
