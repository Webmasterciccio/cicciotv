import { useState } from 'react'
import { importItem, searchCatalog } from '../api.js'
import Poster from '../components/Poster.jsx'
import Suggestions from '../components/Suggestions.jsx'
import { MEDIA_TYPES, searchPlaceholder, suggestionsTitle } from '../mediaMeta.js'

function addLabel(state) {
  if (state === 'adding') return 'Aggiungo…'
  if (state === 'added') return 'Aggiunto ✓'
  if (state === 'exists') return 'Già in libreria'
  if (state === 'error') return 'Riprova'
  return 'Aggiungi'
}

function Search() {
  const [mediaType, setMediaType] = useState('tv')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [addState, setAddState] = useState({}) // external_id -> stato

  async function handleSubmit(event) {
    event.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    try {
      const data = await searchCatalog(query.trim(), mediaType)
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
              const sub = [
                item.first_air_date?.slice(0, 4),
                (item.authors || [])[0],
              ]
                .filter(Boolean)
                .join(' · ')
              return (
                <div key={`${item.source}-${item.external_id}`} className="search-result">
                  <Poster url={item.poster_url} title={item.title} />
                  <div className="search-result-body">
                    <h3>{item.title}</h3>
                    <p className="hint">{sub || 'Data sconosciuta'}</p>
                    {item.overview && <p className="overview">{item.overview}</p>}
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
        </>
      )}

      {/* Consigli (quando non stai cercando) */}
      {results === null && (
        <Suggestions mediaType={mediaType} title={suggestionsTitle(mediaType)} />
      )}
    </div>
  )
}

export default Search
