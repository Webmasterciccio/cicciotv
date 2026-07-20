import { Link } from 'react-router-dom'
import Poster from './Poster.jsx'

function SeriesCard({ series }) {
  const isMovie = series.media_type === 'movie'
  return (
    <Link to={`/serie/${series.id}`} className="series-card">
      <div className="series-card-poster">
        <Poster url={series.poster_url} title={series.title} />
        {isMovie && <span className="media-badge">Film</span>}
      </div>
      <div className="series-card-body">
        <h3>{series.title}</h3>
        <p className="series-card-meta">
          {isMovie ? (
            <>
              {series.rating != null && <span>★ {series.rating}/10</span>}
              {series.rating == null && series.runtime != null && <span>{series.runtime} min</span>}
            </>
          ) : (
            <>
              {series.status === 'in_corso' && series.current_season != null && (
                <span>
                  S{series.current_season} · E{series.current_episode}
                </span>
              )}
              {series.status === 'vista' && series.rating != null && (
                <span>★ {series.rating}/10</span>
              )}
              {series.status === 'da_vedere' && series.total_seasons != null && (
                <span>
                  {series.total_seasons} stagion{series.total_seasons === 1 ? 'e' : 'i'}
                </span>
              )}
            </>
          )}
        </p>
      </div>
    </Link>
  )
}

export default SeriesCard
