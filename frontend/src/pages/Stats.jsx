import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getStats } from '../api.js'
import MonthlyChart from '../components/MonthlyChart.jsx'
import WeekdayChart from '../components/WeekdayChart.jsx'
import { labelOf } from '../mediaMeta.js'

function formatWatchTime(minutes) {
  if (!minutes) return '0 min'
  const days = Math.floor(minutes / 1440)
  const hours = Math.floor((minutes % 1440) / 60)
  const mins = minutes % 60
  const parts = []
  if (days) parts.push(`${days}g`)
  if (hours) parts.push(`${hours}h`)
  if (mins && !days) parts.push(`${mins}min`)
  return parts.join(' ') || '0 min'
}

function Stats() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getStats()
      .then(setStats)
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <p className="error">Errore nel caricamento delle statistiche: {error}</p>
  if (stats === null) return <p className="hint">Caricamento…</p>

  const cards = [
    { label: 'Serie totali', value: stats.total_series },
    { label: 'In corso', value: stats.watching, accent: true },
    { label: 'Da vedere', value: stats.to_watch },
    { label: 'Completate', value: stats.completed },
    { label: 'Episodi visti', value: stats.episodes_watched },
    { label: 'Tempo di visione', value: formatWatchTime(stats.minutes_watched) },
    {
      label: 'Voto medio',
      value: stats.average_rating != null ? `★ ${stats.average_rating}` : '—',
      sub: stats.rated_count ? `su ${stats.rated_count} valutate` : null,
    },
  ]

  const m = stats.movies
  const movieCards = [
    { label: 'Film totali', value: m.total },
    { label: 'Da vedere', value: m.to_watch },
    { label: 'Visti', value: m.watched, accent: true },
    { label: 'Tempo di visione', value: formatWatchTime(m.minutes_watched) },
    {
      label: 'Voto medio',
      value: m.average_rating != null ? `★ ${m.average_rating}` : '—',
      sub: m.rated_count ? `su ${m.rated_count} valutati` : null,
    },
  ]

  return (
    <div className="stats-page">
      <h1>Statistiche</h1>

      {(stats.by_type || []).length > 0 && (
        <section className="by-type-section">
          <h2 className="stats-heading">Panoramica per tipo</h2>
          <div className="by-type-grid">
            {stats.by_type.map((t) => (
              <div key={t.media_type} className="by-type-card">
                <span className="by-type-label">{labelOf(t.media_type)}</span>
                <span className="by-type-total">{t.total}</span>
                <span className="by-type-breakdown hint">
                  {t.in_progress > 0 && <>{t.in_progress} in corso · </>}
                  {t.to_watch} da fare · {t.completed} finiti
                  {t.average_rating != null && <> · ★ {t.average_rating}</>}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {stats.watch_insights.length > 0 && (
        <section className="insights-section">
          <h2>Le tue abitudini</h2>
          <div className="insights">
            {stats.watch_insights.map((text, i) => (
              <div key={i} className="insight-card">
                {text}
              </div>
            ))}
          </div>
        </section>
      )}

      <h2 className="stats-heading">Serie TV</h2>
      <div className="stats-grid">
        {cards.map((c) => (
          <div key={c.label} className={`stat-card${c.accent ? ' stat-card-accent' : ''}`}>
            <span className="stat-value">{c.value}</span>
            <span className="stat-label">{c.label}</span>
            {c.sub && <span className="stat-sub hint">{c.sub}</span>}
          </div>
        ))}
      </div>

      <h2 className="stats-heading">Film</h2>
      <div className="stats-grid">
        {movieCards.map((c) => (
          <div key={c.label} className={`stat-card${c.accent ? ' stat-card-accent' : ''}`}>
            <span className="stat-value">{c.value}</span>
            <span className="stat-label">{c.label}</span>
            {c.sub && <span className="stat-sub hint">{c.sub}</span>}
          </div>
        ))}
      </div>

      <div className="month-card">
        <span className="month-card-title">
          Questo mese hai visto {m.this_month.total} film
        </span>
        <div className="month-card-items">
          <span className="month-item">
            <span className="month-emoji">🎬</span> <strong>{m.this_month.cinema}</strong> al cinema
          </span>
          <span className="month-item">
            <span className="month-emoji">📺</span> <strong>{m.this_month.tv}</strong> in TV
          </span>
          <span className="month-item">
            <span className="month-emoji">▶️</span> <strong>{m.this_month.streaming}</strong> in
            streaming
          </span>
        </div>
      </div>

      {stats.episodes_per_month.length > 0 && (
        <section className="chart-section">
          <h2>Episodi visti per mese</h2>
          <MonthlyChart data={stats.episodes_per_month} />
        </section>
      )}

      {stats.episodes_by_weekday.some((d) => d.count > 0) && (
        <section className="chart-section">
          <h2>Quando guardi</h2>
          <WeekdayChart data={stats.episodes_by_weekday} />
        </section>
      )}

      {stats.in_progress.length > 0 && (
        <section className="progress-section">
          <h2>Completamento serie in corso</h2>
          <div className="progress-list">
            {stats.in_progress.map((s) => (
              <Link key={s.id} to={`/serie/${s.id}`} className="progress-item">
                <div className="progress-item-head">
                  <span className="progress-title">{s.title}</span>
                  <span className="hint">
                    {s.watched}/{s.total} · {s.percent}%
                  </span>
                </div>
                <div className="progress-track">
                  <div className="progress-fill" style={{ width: `${s.percent}%` }} />
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {stats.top_series.length > 0 && (
        <section className="top-series">
          <h2>Le tue serie più viste</h2>
          <ol className="top-series-list">
            {stats.top_series.map((s, i) => (
              <li key={s.id}>
                <span className="top-rank">{i + 1}</span>
                <Link to={`/serie/${s.id}`} className="top-title">
                  {s.title}
                </Link>
                <span className="hint">{s.episodes_watched} ep</span>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  )
}

export default Stats
