import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listSeries } from '../api.js'
import SeriesCard from '../components/SeriesCard.jsx'
import Suggestions from '../components/Suggestions.jsx'
import { MEDIA_TYPES, emptyLibrary, sections, suggestionsTitle } from '../mediaMeta.js'

// Tab per stato del tipo di media corrente. Per la tv lo stato "in_corso" si
// divide in "In pari" (nessun episodio uscito ancora da vedere) e "In corso"
// (episodi usciti da recuperare), stesso split gia' usato prima quando le
// sezioni erano impilate una sotto l'altra.
function buildTabs(mediaType, library) {
  const secs = sections(mediaType)
  const tabs = []
  for (const { status, title } of secs) {
    if (mediaType === 'tv' && status === 'in_corso') {
      tabs.push({
        key: 'caught_up',
        title: 'In pari',
        items: library.filter((s) => s.status === 'in_corso' && s.caught_up),
      })
      tabs.push({
        key: 'in_corso',
        title,
        items: library.filter((s) => s.status === 'in_corso' && !s.caught_up),
      })
    } else {
      tabs.push({ key: status, title, items: library.filter((s) => s.status === status) })
    }
  }
  return tabs
}

function Dashboard() {
  const [mediaType, setMediaType] = useState('tv')
  const [statusTab, setStatusTab] = useState(null)
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
  const tabs = buildTabs(mediaType, library)

  // La tab selezionata resta valida finche' esiste per questo tipo di media;
  // altrimenti (primo caricamento o cambio tipo) si sceglie la prima non
  // vuota, cosi' non si atterra mai su una tab vuota senza motivo.
  let activeKey = statusTab
  if (!tabs.some((t) => t.key === activeKey)) {
    const firstNonEmpty = tabs.find((t) => t.items.length > 0)
    activeKey = (firstNonEmpty || tabs[0])?.key ?? null
  }
  const activeTab = tabs.find((t) => t.key === activeKey)

  function changeType(type) {
    setMediaType(type)
    setStatusTab(null)
  }

  return (
    <div className="dashboard">
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

      {library.length === 0 ? (
        <>
          <p className="hint">
            {emptyLibrary(mediaType)} Cerca in <Link to="/cerca">Cerca</Link> oppure aggiungi uno
            dei consigli qui sotto.
          </p>
          <Suggestions mediaType={mediaType} title={suggestionsTitle(mediaType)} />
        </>
      ) : (
        <>
          <div className="type-toggle type-toggle-scroll status-tabs">
            {tabs.map((t) => (
              <button
                key={t.key}
                type="button"
                className={activeKey === t.key ? 'on' : ''}
                onClick={() => setStatusTab(t.key)}
              >
                {t.title} <span className="count">{t.items.length}</span>
              </button>
            ))}
          </div>
          <section className="dashboard-section">
            {!activeTab || activeTab.items.length === 0 ? (
              <p className="hint">Nessun titolo qui.</p>
            ) : (
              <div className="series-grid">
                {activeTab.items.map((s) => (
                  <SeriesCard key={s.id} series={s} />
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}

export default Dashboard
