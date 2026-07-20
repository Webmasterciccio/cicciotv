import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listSeries } from '../api.js'
import SeriesCard from '../components/SeriesCard.jsx'
import Suggestions from '../components/Suggestions.jsx'

// Sezioni (stati) diverse per tipo: i film non hanno lo stato "in corso".
const SECTIONS = {
  tv: [
    { status: 'in_corso', title: 'In corso' },
    { status: 'da_vedere', title: 'Da vedere' },
    { status: 'vista', title: 'Viste' },
  ],
  movie: [
    { status: 'da_vedere', title: 'Da vedere' },
    { status: 'vista', title: 'Visti' },
  ],
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
  const sections = SECTIONS[mediaType]

  return (
    <div className="dashboard">
      <div className="type-toggle">
        <button
          type="button"
          className={mediaType === 'tv' ? 'on' : ''}
          onClick={() => setMediaType('tv')}
        >
          Serie TV
        </button>
        <button
          type="button"
          className={mediaType === 'movie' ? 'on' : ''}
          onClick={() => setMediaType('movie')}
        >
          Film
        </button>
      </div>

      {library.length === 0 ? (
        <>
          <p className="hint">
            {mediaType === 'movie'
              ? 'Non hai ancora film in libreria.'
              : 'Non hai ancora serie in libreria.'}{' '}
            Cerca in <Link to="/cerca">Cerca</Link> oppure aggiungi uno dei consigli qui sotto.
          </p>
          <Suggestions
            mediaType={mediaType}
            title={mediaType === 'movie' ? 'Film consigliati per te' : 'Serie consigliate per te'}
          />
        </>
      ) : (
        sections.map(({ status, title }) => {
          const items = library.filter((s) => s.status === status)
          return (
            <section key={status} className="dashboard-section">
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
        })
      )}
    </div>
  )
}

export default Dashboard
