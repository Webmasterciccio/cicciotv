// Nell'app Android "127.0.0.1" e' il telefono stesso, non il PC: va usato
// l'indirizzo LAN del PC (vedi frontend/.env). Nel browser desktop il default
// resta localhost.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

async function request(path, options = {}) {
  const url = `${API_BASE_URL}${path}`
  let response
  try {
    response = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    })
  } catch (err) {
    // Un fetch() fallito a livello di rete (DNS, connessione rifiutata, CORS,
    // cleartext bloccato...) da' solo un generico "Failed to fetch": il
    // browser/WebView nasconde il motivo esatto per motivi di sicurezza.
    // Qui aggiungiamo almeno l'URL tentato per capire dove si e' fermato.
    const error = new Error(`Rete non raggiungibile su ${url} (${err.name}: ${err.message})`)
    error.cause = err
    throw error
  }

  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = await response.json()
      detail = body.detail ?? detail
    } catch {
      // corpo non-JSON, si tiene lo statusText
    }
    const error = new Error(detail)
    error.status = response.status
    throw error
  }

  if (response.status === 204) return null
  return response.json()
}

// --- Serie ---

export function listSeries(status) {
  const query = status ? `?status=${status}` : ''
  return request(`/series${query}`)
}

export function getSeries(id) {
  return request(`/series/${id}`)
}

export function updateSeries(id, patch) {
  return request(`/series/${id}`, { method: 'PATCH', body: JSON.stringify(patch) })
}

export function deleteSeries(id) {
  return request(`/series/${id}`, { method: 'DELETE' })
}

// --- TMDB ---

export function searchTmdb(query, type = 'tv') {
  return request(`/tmdb/search?query=${encodeURIComponent(query)}&type=${type}`)
}

export function importFromTmdb(tmdbId, status = 'da_vedere', type = 'tv') {
  return request(`/tmdb/import/${tmdbId}?status=${status}&type=${type}`, { method: 'POST' })
}

export function getGenres(type = 'tv') {
  return request(`/tmdb/genres?type=${type}`)
}

export function getSuggestions(limit = 20, type = 'tv') {
  return request(`/tmdb/suggestions?limit=${limit}&type=${type}`)
}

// --- Impostazioni & statistiche ---

export function getSettings() {
  return request('/settings')
}

export function updateSettings(patch) {
  return request('/settings', { method: 'PUT', body: JSON.stringify(patch) })
}

export function getStats() {
  return request('/stats')
}

// --- Episodi ---

export function getEpisodes(seriesId) {
  return request(`/series/${seriesId}/episodes`)
}

export function getWatchProviders(seriesId) {
  return request(`/series/${seriesId}/watch-providers`)
}

export function getTmdbDetails(seriesId) {
  return request(`/series/${seriesId}/tmdb`)
}

export function getRecommendations(seriesId) {
  return request(`/series/${seriesId}/recommendations`)
}

export function syncEpisodes(seriesId) {
  return request(`/series/${seriesId}/episodes/sync`, { method: 'POST' })
}

export function setEpisodeWatched(seriesId, episodeId, watched) {
  return request(`/series/${seriesId}/episodes/${episodeId}`, {
    method: 'PATCH',
    body: JSON.stringify({ watched }),
  })
}

export function watchEpisodesUpTo(seriesId, episodeId) {
  return request(`/series/${seriesId}/episodes/${episodeId}/watch-up-to`, { method: 'POST' })
}

export function setSeasonWatched(seriesId, seasonNumber, watched) {
  return request(`/series/${seriesId}/seasons/${seasonNumber}`, {
    method: 'PATCH',
    body: JSON.stringify({ watched }),
  })
}
