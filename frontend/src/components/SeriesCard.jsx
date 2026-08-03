import { Link } from 'react-router-dom'
import Poster from './Poster.jsx'
import { hasProgress, labelOf, unitLabel } from '../mediaMeta.js'

function SeriesCard({ series }) {
  const type = series.media_type || 'tv'
  const badge = type === 'tv' ? null : labelOf(type)

  // Riga meta: dipende dal tipo e dallo stato.
  let meta = null
  if (series.status === 'vista' && series.rating != null) {
    meta = <span>★ {series.rating}/10</span>
  } else if (hasProgress(type) && series.status === 'in_corso' && series.progress_total) {
    meta = (
      <span>
        {series.progress_current || 0}/{series.progress_total} {unitLabel(type)}
      </span>
    )
  } else if (type === 'tv' && series.status === 'in_corso' && series.current_season != null) {
    meta = (
      <span>
        S{series.current_season} · E{series.current_episode}
      </span>
    )
  } else if (type === 'movie' && series.rating == null && series.runtime != null) {
    meta = <span>{series.runtime} min</span>
  } else if (series.status === 'da_vedere' && series.progress_total) {
    meta = (
      <span>
        {series.progress_total} {unitLabel(type)}
      </span>
    )
  } else if (type === 'tv' && series.status === 'da_vedere' && series.total_seasons != null) {
    meta = (
      <span>
        {series.total_seasons} stagion{series.total_seasons === 1 ? 'e' : 'i'}
      </span>
    )
  }

  return (
    <Link to={`/serie/${series.id}`} className="series-card">
      <div className="series-card-poster">
        <Poster url={series.poster_url} title={series.title} />
        {badge && <span className="media-badge">{badge}</span>}
      </div>
      <div className="series-card-body">
        <h3>{series.title}</h3>
        <p className="series-card-meta">{meta}</p>
      </div>
    </Link>
  )
}

export default SeriesCard
