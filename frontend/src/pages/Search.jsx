import { useState } from 'react'
import { importFromTmdb, searchTmdb } from '../api.js'
import Poster from '../components/Poster.jsx'
import Suggestions from '../components/Suggestions.jsx'

function Search() {
  const [mediaType, setMediaType] = useState('tv')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [addState, setAddState] = useState({}) // tmdb_id -> 'adding' | 'added' | 'exists' | 'error'

  async function handleSubmit(event) {
    event.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    try {
      const data = await searchTmdb(query.trim(), mediaType)
      setResults(data)
      setAddState({})
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
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
    <div className="search-page">
      <div className="type-toggle">
        <button
          type="button"
          className={mediaType === 'tv' ? 'on' : ''}
          onClick={() => changeType('tv')}
        >
          Serie TV
        </button>
        <button
          type="button"
          className={mediaType === 'movie' ? 'on' : ''}
          onClick={() => changeType('movie')}
        >
          Film
        </button>
      </div>

      <form onSubmit={handleSubmit} className="search-form">
        <input
          type="text"
          placeholder={mediaType === 'movie' ? 'Cerca un film…' : 'Cerca una serie TV…'}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Cerco…' : 'Cerca'}
        </button>
      </form>

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
              const state = addState[item.tmdb_id]
              return (
                <div key={item.tmdb_id} className="search-result">
                  <Poster url={item.poster_url} title={item.title} />
                  <div className="search-result-body">
                    <h3>{item.title}</h3>
                    <p className="hint">{item.first_air_date?.slice(0, 4) || 'Data sconosciuta'}</p>
                    {item.overview && <p className="overview">{item.overview}</p>}
                    <button
                      type="button"
                      onClick={() => handleAdd(item.tmdb_id)}
                      disabled={state === 'adding' || state === 'added' || state === 'exists'}
                    >
                      {state === 'adding' && 'Aggiungo…'}
                      {state === 'added' && 'Aggiunta ✓'}
                      {state === 'exists' && "Già in libreria"}
                      {state === 'error' && 'Riprova'}
                      {!state && 'Aggiungi'}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}

      {/* Consigli in base ai generi preferiti (quando non stai cercando) */}
      {results === null && (
        <Suggestions
          mediaType={mediaType}
          title={mediaType === 'movie' ? 'Film consigliati per te' : 'Serie consigliate per te'}
        />
      )}
    </div>
  )
}

export default Search
