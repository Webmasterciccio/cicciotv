function Poster({ url, title }) {
  if (url) {
    return <img className="poster" src={url} alt={title} loading="lazy" />
  }
  return (
    <div className="poster poster-placeholder" aria-hidden="true">
      {title ? title.slice(0, 1).toUpperCase() : '?'}
    </div>
  )
}

export default Poster
