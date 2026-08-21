import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  deleteSeries,
  getEpisodes,
  getMediaDetails,
  getRecommendations,
  getSeries,
  getWatchProviders,
  importItem,
  setEpisodeWatched,
  setSeasonWatched,
  syncEpisodes,
  updateSeries,
  watchEpisodesUpTo,
} from '../api.js'
import Poster from '../components/Poster.jsx'
import ProgressTracker from '../components/ProgressTracker.jsx'
import { hasProgress, hasUnitList, statusLabels, unitLabel } from '../mediaMeta.js'

// Etichette leggibili per le categorie di servizi restituite da TMDB.
const PROVIDER_KIND_LABELS = {
  flatrate: 'Abbonamento',
  free: 'Gratis',
  ads: 'Con pubblicità',
  rent: 'Noleggio',
  buy: 'Acquisto',
}

// Stato TMDB -> italiano (serie e film).
const TMDB_STATUS_LABELS = {
  'Returning Series': 'In corso',
  Ended: 'Conclusa',
  Canceled: 'Cancellata',
  'In Production': 'In produzione',
  Planned: 'Pianificata',
  Pilot: 'Pilota',
  Released: 'Uscito',
  'Post Production': 'Post-produzione',
  Rumored: 'Non confermato',
}

function groupBySeason(episodes) {
  const seasons = new Map()
  for (const ep of episodes) {
    if (!seasons.has(ep.season_number)) seasons.set(ep.season_number, [])
    seasons.get(ep.season_number).push(ep)
  }
  return [...seasons.entries()].sort(([a], [b]) => a - b)
}

function formatDate(value) {
  if (!value) return null
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return value
  return dt.toLocaleDateString('it-IT', { day: 'numeric', month: 'short', year: 'numeric' })
}

function yearOf(value) {
  return value ? value.slice(0, 4) : null
}

function SeriesDetail() {
  const { id } = useParams()
  const navigate = useNavigate()

  const [series, setSeries] = useState(null)
  const [episodes, setEpisodes] = useState(null)
  const [providers, setProviders] = useState(null)
  const [details, setDetails] = useState(null)
  const [recommendations, setRecommendations] = useState([])
  const [openSeasons, setOpenSeasons] = useState(null)
  const [error, setError] = useState(null)
  const [syncing, setSyncing] = useState(false)
  const backfilledRef = useRef(false)

  const load = useCallback(async () => {
    try {
      const [seriesData, episodesData, providersData, detailsData, recsData] = await Promise.all([
        getSeries(id),
        getEpisodes(id),
        getWatchProviders(id),
        getMediaDetails(id),
        getRecommendations(id),
      ])
      setSeries(seriesData)
      setEpisodes(episodesData)
      setProviders(providersData)
      setDetails(detailsData)
      setRecommendations(recsData)
    } catch (err) {
      setError(err.message)
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  // Alla prima comparsa degli episodi, apre le stagioni non ancora completate
  // e tiene chiuse quelle gia' viste (la fisarmonica resta poi controllata dall'utente).
  useEffect(() => {
    if (episodes && openSeasons === null) {
      const init = {}
      for (const [seasonNumber, eps] of groupBySeason(episodes)) {
        init[seasonNumber] = !eps.every((e) => e.watched)
      }
      setOpenSeasons(init)
    }
  }, [episodes, openSeasons])

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

  // Serie importate prima di questa versione non hanno le miniature: le
  // recuperiamo una volta sola risincronizzando in automatico da TMDB.
  useEffect(() => {
    if (
      !backfilledRef.current &&
      series?.tmdb_id != null &&
      episodes &&
      episodes.length > 0 &&
      episodes.every((e) => !e.still_url)
    ) {
      backfilledRef.current = true
      handleSync()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [series, episodes])

  async function handleStatusChange(newStatus) {
    const updated = await updateSeries(id, { status: newStatus })
    setSeries(updated)
  }

  async function handleRatingChange(newRating) {
    const updated = await updateSeries(id, { rating: newRating })
    setSeries(updated)
  }

  async function handleLocationChange(loc) {
    const updated = await updateSeries(id, { watch_location: loc || null })
    setSeries(updated)
  }

  async function handleDelete() {
    if (!window.confirm(`Eliminare "${series.title}" dalla libreria?`)) return
    await deleteSeries(id)
    navigate('/')
  }

  async function refreshSeriesAndEpisodes() {
    const [seriesData, episodesData] = await Promise.all([getSeries(id), getEpisodes(id)])
    setSeries(seriesData)
    setEpisodes(episodesData)
  }

  async function handleEpisodeToggle(episode, watched) {
    // Se segno visto un episodio "distante" (con episodi precedenti ancora da
    // vedere), chiedo se aggiungere anche tutti quelli prima.
    if (watched) {
      const before = (a, b) =>
        a.season_number < b.season_number ||
        (a.season_number === b.season_number && a.episode_number < b.episode_number)
      const earlierUnwatched = episodes.filter((e) => before(e, episode) && !e.watched)
      if (earlierUnwatched.length > 0) {
        const ok = window.confirm(
          `Aggiungere come visti anche i ${earlierUnwatched.length} episodi precedenti?`,
        )
        if (ok) {
          const updated = await watchEpisodesUpTo(id, episode.id)
          setEpisodes(updated)
          setSeries(await getSeries(id))
          return
        }
      }
    }
    await setEpisodeWatched(id, episode.id, watched)
    await refreshSeriesAndEpisodes()
  }

  async function handleAddRecommendation(rec) {
    try {
      const created = await importItem(rec, 'da_vedere')
      navigate(`/serie/${created.id}`)
    } catch (err) {
      if (err.status === 409) {
        window.alert('Questo titolo è già nella tua libreria.')
      } else {
        window.alert(`Impossibile aggiungere: ${err.message}`)
      }
    }
  }

  async function handleProgressChange(next) {
    const updated = await updateSeries(id, { progress_current: next })
    setSeries(updated)
  }

  async function handleSeasonToggle(seasonNumber, watched) {
    await setSeasonWatched(id, seasonNumber, watched)
    const [seriesData, episodesData] = await Promise.all([getSeries(id), getEpisodes(id)])
    setSeries(seriesData)
    setEpisodes(episodesData)
  }

  if (error) return <p className="error">Errore: {error}</p>
  if (series === null) return <p className="hint">Caricamento…</p>

  const type = series.media_type || 'tv'
  const seasons = groupBySeason(episodes ?? [])
  const d = details ?? {}
  const isMovie = type === 'movie'
  const labels = statusLabels(type)
  const statusOptions = isMovie ? { da_vedere: labels.da_vedere, vista: labels.vista } : labels
  const showUnits = hasUnitList(type) // tv/comic → lista episodi/numeri
  const showProgress = hasProgress(type) // manga/libri → progresso numerico
  const unitsTitle = type === 'comic' ? 'Numeri' : type === 'manga' ? 'Volumi' : 'Episodi'

  // Etichetta del titolo di credito, diversa per sorgente. Per "tv" copre sia
  // le serie TMDB (creata da) sia gli anime da AniList/Jikan (d.created_by
  // contiene lo studio in quel caso).
  const creditLabel = { tv: 'Creata da', movie: 'Regia di', manga: 'Autore', book: 'Autore', comic: 'Editore' }[type]
  const credit =
    type === 'comic'
      ? d.publisher
      : (d.authors?.length ? d.authors.join(', ') : (d.created_by || []).join(', '))

  // Riga di metadati compatta (solo le voci disponibili).
  const typeBadge = { movie: 'Film', manga: 'Manga', book: 'Libro', comic: 'Fumetto' }[type]
  const metaItems = []
  if (typeBadge) metaItems.push(typeBadge)
  const startYear = yearOf(d.first_air_date)
  const endYear = yearOf(d.last_air_date)
  if (startYear) {
    metaItems.push(startYear === endYear || !endYear ? startYear : `${startYear}–${endYear}`)
  }
  if (d.status) metaItems.push(TMDB_STATUS_LABELS[d.status] ?? d.status)
  if (d.number_of_seasons)
    metaItems.push(`${d.number_of_seasons} stagion${d.number_of_seasons === 1 ? 'e' : 'i'}`)
  if (d.number_of_episodes) metaItems.push(`${d.number_of_episodes} ${unitLabel(type)}`)
  if (d.volumes) metaItems.push(`${d.volumes} volumi`)
  if (d.chapters && !showUnits) metaItems.push(`${d.chapters} capitoli`)
  if (d.page_count) metaItems.push(`${d.page_count} pagine`)
  if (d.episode_run_time)
    metaItems.push(isMovie ? `${d.episode_run_time} min` : `~${d.episode_run_time} min/ep`)

  return (
    <div className="series-detail">
      {d.backdrop_url && (
        <div
          className="series-backdrop"
          style={{ backgroundImage: `url(${d.backdrop_url})` }}
          aria-hidden="true"
        />
      )}

      <div className="series-detail-header">
        <Poster url={series.poster_url} title={series.title} />
        <div className="series-detail-info">
          <h1 className="series-title">{series.title}</h1>
          {d.original_title && d.original_title !== series.title && (
            <p className="original-title hint">{d.original_title}</p>
          )}
          {d.tagline && <p className="tagline">«{d.tagline}»</p>}

          {d.genres?.length > 0 && (
            <div className="genres">
              {d.genres.map((g) => (
                <span key={g} className="genre-chip">
                  {g}
                </span>
              ))}
            </div>
          )}

          {metaItems.length > 0 && <p className="meta-line hint">{metaItems.join(' · ')}</p>}

          {d.vote_average ? (
            <p className="tmdb-rating">
              ★ {d.vote_average.toFixed(1)}
              <span className="hint"> / 10 · {d.vote_count?.toLocaleString('it-IT')} voti TMDB</span>
            </p>
          ) : null}

          {credit && (
            <p className="hint">
              <strong>{creditLabel}:</strong> {credit}
            </p>
          )}

          {d.networks?.length > 0 && (
            <div className="networks">
              {d.networks.map((n) =>
                n.logo_url ? (
                  <img key={n.name} src={n.logo_url} alt={n.name} title={n.name} className="network-logo" />
                ) : (
                  <span key={n.name} className="hint">
                    {n.name}
                  </span>
                ),
              )}
            </div>
          )}

          <div className="user-controls">
            <div className="field-row">
              <label htmlFor="status">Stato</label>
              <select
                id="status"
                value={series.status}
                onChange={(e) => handleStatusChange(e.target.value)}
              >
                {Object.entries(statusOptions).map(([value, label]) => (
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

            {isMovie && (
              <div className="field-row">
                <label htmlFor="location">Visto</label>
                <select
                  id="location"
                  value={series.watch_location ?? ''}
                  onChange={(e) => handleLocationChange(e.target.value)}
                >
                  <option value="">—</option>
                  <option value="cinema">Al cinema</option>
                  <option value="streaming">In streaming</option>
                  <option value="tv">In TV</option>
                </select>
              </div>
            )}

            {series.current_season != null && (
              <p className="hint">
                {type === 'manga'
                  ? `Progresso: Volume ${series.current_episode}`
                  : `Progresso: S${series.current_season} · E${series.current_episode}`}
              </p>
            )}

            {d.homepage && (
              <a className="provider-link" href={d.homepage} target="_blank" rel="noreferrer">
                Sito ufficiale →
              </a>
            )}

            <button type="button" className="danger" onClick={handleDelete}>
              Elimina serie
            </button>
          </div>
        </div>
      </div>

      {d.overview && (
        <section className="overview-section">
          <h2>Trama</h2>
          <p>{d.overview}</p>
        </section>
      )}

      {providers && Object.keys(providers.providers).length > 0 && (
        <section className="watch-providers">
          <h2>Dove vederla</h2>
          <div className="provider-groups">
            {Object.entries(providers.providers).map(([kind, list]) => (
              <div key={kind} className="provider-group">
                <span className="provider-kind">{PROVIDER_KIND_LABELS[kind] ?? kind}</span>
                <div className="provider-logos">
                  {list.map((p) => (
                    <span key={p.name} className="provider-chip" title={p.name}>
                      {p.logo_url ? (
                        <img src={p.logo_url} alt={p.name} loading="lazy" />
                      ) : (
                        <span className="provider-name">{p.name}</span>
                      )}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
          {providers.link && (
            <a className="provider-link" href={providers.link} target="_blank" rel="noreferrer">
              Vedi tutte le opzioni →
            </a>
          )}
        </section>
      )}

      {d.cast?.length > 0 && (
        <section className="cast-section">
          <h2>Cast</h2>
          <div className="cast-row">
            {d.cast.map((p) => (
              <div key={`${p.name}-${p.character}`} className="cast-card">
                {p.profile_url ? (
                  <img src={p.profile_url} alt={p.name} loading="lazy" className="cast-photo" />
                ) : (
                  <div className="cast-photo cast-photo-empty" aria-hidden="true">
                    {p.name?.slice(0, 1)}
                  </div>
                )}
                <span className="cast-name">{p.name}</span>
                {p.character && <span className="cast-character hint">{p.character}</span>}
              </div>
            ))}
          </div>
        </section>
      )}

      {d.seasons?.length > 0 && (
        <section className="seasons-section">
          <h2>Stagioni</h2>
          <div className="seasons-grid">
            {d.seasons.map((s) => (
              <div key={s.season_number} className="season-card">
                <Poster url={s.poster_url} title={s.name} />
                <div className="season-card-body">
                  <h3>{s.name}</h3>
                  <p className="hint season-card-meta">
                    {[
                      s.episode_count ? `${s.episode_count} episodi` : null,
                      yearOf(s.air_date),
                    ]
                      .filter(Boolean)
                      .join(' · ')}
                  </p>
                  {s.overview && <p className="season-card-overview hint">{s.overview}</p>}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {showProgress && (
        <section className="progress-section">
          <h2>Progresso di lettura</h2>
          <ProgressTracker series={series} onChange={handleProgressChange} />
        </section>
      )}

      {showUnits && (
      <section className="episodes-section">
        <h2>{unitsTitle}</h2>

        {series.external_id == null && (
          <p className="hint">Titolo non collegato alla sorgente: tracciamento non disponibile.</p>
        )}

        {series.external_id != null && seasons.length === 0 && (
          <button type="button" onClick={handleSync} disabled={syncing}>
            {syncing ? 'Sincronizzo…' : `Sincronizza ${unitLabel(type)}`}
          </button>
        )}

        {seasons.map(([seasonNumber, eps]) => {
          const watchedCount = eps.filter((e) => e.watched).length
          const allWatched = watchedCount === eps.length
          const isOpen = openSeasons?.[seasonNumber] ?? true
          return (
            <details key={seasonNumber} className="season-group" open={isOpen}>
              <summary
                className="season-header"
                onClick={(e) => {
                  // React controlla 'open' via stato: blocchiamo il toggle nativo
                  // del browser e aggiorniamo noi lo stato (niente loop con onToggle).
                  e.preventDefault()
                  setOpenSeasons((prev) => ({ ...prev, [seasonNumber]: !isOpen }))
                }}
              >
                <span className="season-title">
                  <span className="season-chevron" aria-hidden="true">▸</span>
                  Stagione {seasonNumber}
                  <span className="count">
                    {watchedCount}/{eps.length}
                  </span>
                </span>
                <button
                  type="button"
                  className="season-toggle-btn"
                  onClick={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    handleSeasonToggle(seasonNumber, !allWatched)
                  }}
                >
                  {allWatched ? 'Deseleziona' : 'Segna tutta'}
                </button>
              </summary>
              <ul className="episode-list">
                {eps.map((ep) => {
                  const sub = [formatDate(ep.air_date), ep.runtime ? `${ep.runtime} min` : null]
                    .filter(Boolean)
                    .join(' · ')
                  const unitPrefix = type === 'comic' ? 'N' : type === 'manga' ? 'Vol. ' : 'E'
                  return (
                    <li key={ep.id} className="episode-item">
                      <label className="episode-label">
                        <input
                          type="checkbox"
                          className="episode-check"
                          checked={ep.watched}
                          onChange={(e) => handleEpisodeToggle(ep, e.target.checked)}
                        />
                        {ep.still_url ? (
                          <img className="episode-still" src={ep.still_url} alt="" loading="lazy" />
                        ) : (
                          <div className="episode-still episode-still-empty" aria-hidden="true">
                            {unitPrefix}{ep.episode_number}
                          </div>
                        )}
                        <div className="episode-text">
                          <div className="episode-head">
                            <span className="episode-number">{unitPrefix}{ep.episode_number}</span>
                            {type !== 'manga' && <span className="episode-name">{ep.name}</span>}
                            {ep.vote_average ? (
                              <span className="episode-vote">★ {ep.vote_average.toFixed(1)}</span>
                            ) : null}
                          </div>
                          {sub && <div className="episode-sub hint">{sub}</div>}
                          {ep.overview && <p className="episode-overview">{ep.overview}</p>}
                        </div>
                      </label>
                    </li>
                  )
                })}
              </ul>
            </details>
          )
        })}
      </section>
      )}

      {recommendations.length > 0 && (
        <section className="recommendations-section">
          <h2>Consigliati simili</h2>
          <div className="recommendations-row">
            {recommendations.map((rec) => (
              <button
                key={`${rec.source}-${rec.external_id}`}
                type="button"
                className="rec-card"
                onClick={() => handleAddRecommendation(rec)}
                title={`Aggiungi "${rec.title}" alla libreria`}
              >
                <Poster url={rec.poster_url} title={rec.title} />
                <div className="rec-card-body">
                  <span className="rec-title">{rec.title}</span>
                  <span className="rec-meta hint">
                    {[rec.vote_average ? `★ ${rec.vote_average.toFixed(1)}` : null, yearOf(rec.first_air_date)]
                      .filter(Boolean)
                      .join(' · ')}
                  </span>
                </div>
                <span className="rec-add" aria-hidden="true">＋</span>
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

export default SeriesDetail
