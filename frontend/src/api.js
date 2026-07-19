const API_BASE_URL = 'http://127.0.0.1:8000'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

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

export function searchTmdb(query) {
  return request(`/tmdb/search?query=${encodeURIComponent(query)}`)
}

export function importFromTmdb(tmdbId, status = 'da_vedere') {
  return request(`/tmdb/import/${tmdbId}?status=${status}`, { method: 'POST' })
}

// --- Episodi ---

export function getEpisodes(seriesId) {
  return request(`/series/${seriesId}/episodes`)
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

export function setSeasonWatched(seriesId, seasonNumber, watched) {
  return request(`/series/${seriesId}/seasons/${seasonNumber}`, {
    method: 'PATCH',
    body: JSON.stringify({ watched }),
  })
}
