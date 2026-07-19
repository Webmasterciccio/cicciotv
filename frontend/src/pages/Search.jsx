import { useState } from 'react'
import { importFromTmdb, searchTmdb } from '../api.js'
import Poster from '../components/Poster.jsx'

function Search() {
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
      const data = await searchTmdb(query.trim())
      setResults(data)
      setAddState({})
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleAdd(tmdbId) {
    setAddState((prev) => ({ ...prev, [tmdbId]: 'adding' }))
    try {
      await importFromTmdb(tmdbId, 'da_vedere')
      setAddState((prev) => ({ ...prev, [tmdbId]: 'added' }))
    } catch (err) {
      setAddState((prev) => ({ ...prev, [tmdbId]: err.status === 409 ? 'exists' : 'error' }))
    }
  }

  return (
    <div className="search-page">
      <form onSubmit={handleSubmit} className="search-form">
        <input
          type="text"
          placeholder="Cerca una serie TV…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Cerco…' : 'Cerca'}
        </button>
      </form>

      {error && <p className="error">Errore nella ricerca: {error}</p>}

      {results !== null && results.length === 0 && <p className="hint">Nessun risultato.</p>}

      <div className="search-results">
        {results?.map((item) => {
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
                  {state === 'exists' && 'Gia\' in libreria'}
                  {state === 'error' && 'Riprova'}
                  {!state && 'Aggiungi'}
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default Search
