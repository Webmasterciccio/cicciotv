import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  deleteSeries,
  getEpisodes,
  getSeries,
  setEpisodeWatched,
  setSeasonWatched,
  syncEpisodes,
  updateSeries,
} from '../api.js'
import Poster from '../components/Poster.jsx'

const STATUS_LABELS = {
  da_vedere: 'Da vedere',
  in_corso: 'In corso',
  vista: 'Vista',
}

function groupBySeason(episodes) {
  const seasons = new Map()
  for (const ep of episodes) {
    if (!seasons.has(ep.season_number)) seasons.set(ep.season_number, [])
    seasons.get(ep.season_number).push(ep)
  }
  return [...seasons.entries()].sort(([a], [b]) => a - b)
}

function SeriesDetail() {
  const { id } = useParams()
  const navigate = useNavigate()

  const [series, setSeries] = useState(null)
  const [episodes, setEpisodes] = useState(null)
  const [error, setError] = useState(null)
  const [syncing, setSyncing] = useState(false)

  const load = useCallback(async () => {
    try {
      const [seriesData, episodesData] = await Promise.all([getSeries(id), getEpisodes(id)])
      setSeries(seriesData)
      setEpisodes(episodesData)
    } catch (err) {
      setError(err.message)
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  async function handleSync() {
    setSyncing(true)
    try {
      const episodesData = await syncEpisodes(id)
      setEpisodes(episodesData)
    } catch (err) {
      setError(err.message)
    } finally {
      setSyncing(false)
    }
  }

  async function handleStatusChange(newStatus) {
    const updated = await updateSeries(id, { status: newStatus })
    setSeries(updated)
  }

  async function handleRatingChange(newRating) {
    const updated = await updateSeries(id, { rating: newRating })
    setSeries(updated)
  }

  async function handleDelete() {
    if (!window.confirm(`Eliminare "${series.title}" dalla libreria?`)) return
    await deleteSeries(id)
    navigate('/')
  }

  async function handleEpisodeToggle(episodeId, watched) {
    await setEpisodeWatched(id, episodeId, watched)
    const [seriesData, episodesData] = await Promise.all([getSeries(id), getEpisodes(id)])
    setSeries(seriesData)
    setEpisodes(episodesData)
  }

  async function handleSeasonToggle(seasonNumber, watched) {
    await setSeasonWatched(id, seasonNumber, watched)
    const [seriesData, episodesData] = await Promise.all([getSeries(id), getEpisodes(id)])
    setSeries(seriesData)
    setEpisodes(episodesData)
  }

  if (error) return <p className="error">Errore: {error}</p>
  if (series === null) return <p className="hint">Caricamento…</p>

  const seasons = groupBySeason(episodes ?? [])

  return (
    <div className="series-detail">
      <div className="series-detail-header">
        <Poster url={series.poster_url} title={series.title} />
        <div className="series-detail-info">
          <h1>{series.title}</h1>

          <div className="field-row">
            <label htmlFor="status">Stato</label>
            <select
              id="status"
              value={series.status}
              onChange={(e) => handleStatusChange(e.target.value)}
            >
              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div className="field-row">
            <label htmlFor="rating">Voto</label>
            <select
              id="rating"
              value={series.rating ?? ''}
              onChange={(e) => handleRatingChange(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">—</option>
              {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>

          {series.current_season != null && (
            <p className="hint">
              Progresso: S{series.current_season} · E{series.current_episode}
            </p>
          )}

          <button type="button" className="danger" onClick={handleDelete}>
            Elimina serie
          </button>
        </div>
      </div>

      <section className="episodes-section">
        <h2>Episodi</h2>

        {series.tmdb_id == null && (
          <p className="hint">Serie non collegata a TMDB: tracciamento episodi non disponibile.</p>
        )}

        {series.tmdb_id != null && seasons.length === 0 && (
          <button type="button" onClick={handleSync} disabled={syncing}>
            {syncing ? 'Sincronizzo…' : 'Sincronizza episodi da TMDB'}
          </button>
        )}

        {seasons.map(([seasonNumber, eps]) => {
          const allWatched = eps.every((e) => e.watched)
          return (
            <div key={seasonNumber} className="season-group">
              <div className="season-header">
                <h3>
                  Stagione {seasonNumber}{' '}
                  <span className="count">
                    {eps.filter((e) => e.watched).length}/{eps.length}
                  </span>
                </h3>
                <button type="button" onClick={() => handleSeasonToggle(seasonNumber, !allWatched)}>
                  {allWatched ? 'Deseleziona stagione' : 'Segna tutta vista'}
                </button>
              </div>
              <ul className="episode-list">
                {eps.map((ep) => (
                  <li key={ep.id}>
                    <label>
                      <input
                        type="checkbox"
                        checked={ep.watched}
                        onChange={(e) => handleEpisodeToggle(ep.id, e.target.checked)}
                      />
                      <span className="episode-number">E{ep.episode_number}</span>
                      <span>{ep.name}</span>
                    </label>
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </section>
    </div>
  )
}

export default SeriesDetail
