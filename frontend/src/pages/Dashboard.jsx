import { Fragment, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listSeries } from '../api.js'
import SeriesCard from '../components/SeriesCard.jsx'
import Suggestions from '../components/Suggestions.jsx'
import { MEDIA_TYPES, emptyLibrary, sections, suggestionsTitle } from '../mediaMeta.js'

function LibrarySection({ title, items }) {
  return (
    <section className="dashboard-section">
      <h2>
        {title} <span className="count">{items.length}</span>
      </h2>
      {items.length === 0 ? (
        <p className="hint">Nessun titolo qui.</p>
      ) : (
        <div className="series-grid">
          {items.map((s) => (
            <SeriesCard key={s.id} series={s} />
          ))}
        </div>
      )}
    </section>
  )
}

function Dashboard() {
  const [mediaType, setMediaType] = useState('tv')
  const [series, setSeries] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    listSeries()
      .then(setSeries)
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <p className="error">Errore nel caricamento della libreria: {error}</p>
  if (series === null) return <p className="hint">Caricamento…</p>

  const library = series.filter((s) => (s.media_type || 'tv') === mediaType)
  const secs = sections(mediaType)

  return (
    <div className="dashboard">
      <div className="type-toggle type-toggle-scroll">
        {MEDIA_TYPES.map((m) => (
          <button
            key={m.type}
            type="button"
            className={mediaType === m.type ? 'on' : ''}
            onClick={() => setMediaType(m.type)}
          >
            {m.label}
          </button>
        ))}
      </div>

      {library.length === 0 ? (
        <>
          <p className="hint">
            {emptyLibrary(mediaType)} Cerca in <Link to="/cerca">Cerca</Link> oppure aggiungi uno
            dei consigli qui sotto.
          </p>
          <Suggestions mediaType={mediaType} title={suggestionsTitle(mediaType)} />
        </>
      ) : (
        secs.map(({ status, title }) => {
          const items = library.filter((s) => s.status === status)
          if (mediaType === 'tv' && status === 'in_corso') {
            const caughtUp = items.filter((s) => s.caught_up)
            const inProgress = items.filter((s) => !s.caught_up)
            return (
              <Fragment key={status}>
                {caughtUp.length > 0 && <LibrarySection title="In pari" items={caughtUp} />}
                <LibrarySection title={title} items={inProgress} />
              </Fragment>
            )
          }
          return <LibrarySection key={status} title={title} items={items} />
        })
      )}
    </div>
  )
}

export default Dashboard
