import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listSeries } from '../api.js'
import SeriesCard from '../components/SeriesCard.jsx'

const SECTIONS = [
  { status: 'in_corso', title: 'In corso' },
  { status: 'da_vedere', title: 'Da vedere' },
  { status: 'vista', title: 'Viste' },
]

function Dashboard() {
  const [series, setSeries] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    listSeries()
      .then(setSeries)
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <p className="error">Errore nel caricamento della libreria: {error}</p>
  if (series === null) return <p className="hint">Caricamento…</p>

  if (series.length === 0) {
    return (
      <p className="hint">
        La libreria e' vuota. Vai su <Link to="/cerca">Cerca</Link> per aggiungere la tua prima serie.
      </p>
    )
  }

  return (
    <div className="dashboard">
      {SECTIONS.map(({ status, title }) => {
        const items = series.filter((s) => s.status === status)
        return (
          <section key={status} className="dashboard-section">
            <h2>
              {title} <span className="count">{items.length}</span>
            </h2>
            {items.length === 0 ? (
              <p className="hint">Nessuna serie qui.</p>
            ) : (
              <div className="series-grid">
                {items.map((s) => (
                  <SeriesCard key={s.id} series={s} />
                ))}
              </div>
            )}
          </section>
        )
      })}
    </div>
  )
}

export default Dashboard
