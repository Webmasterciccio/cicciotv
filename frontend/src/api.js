// Nell'app Android "127.0.0.1" e' il telefono stesso, non il PC: va usato
// l'indirizzo LAN del PC (vedi frontend/.env). Nel browser desktop il default
// resta localhost. In produzione (dietro Caddy sullo stesso dominio) si usa il
// percorso relativo "/api".
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

// Il token di sessione (ottenuto col login via PIN) e' salvato sul dispositivo e
// mandato in ogni richiesta nell'header Authorization. Vale sia per il browser
// che per l'app Android: nessuna password incorporata nel codice.
const TOKEN_KEY = 'cicciotv_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

async function request(path, options = {}) {
  const url = `${API_BASE_URL}${path}`
  const token = getToken()
  let response
  try {
    response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
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

  // Token scaduto/non valido durante l'uso: puliamo e segnaliamo all'app di
  // tornare al login. (Non scatta al login stesso, dove il token non c'e' ancora.)
  if (response.status === 401 && token) {
    setToken(null)
    window.dispatchEvent(new Event('cicciotv:unauthorized'))
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

// --- Autenticazione ---

export function getAuthStatus() {
  return request('/auth/status')
}

export async function login(pin) {
  const res = await request('/auth/login', { method: 'POST', body: JSON.stringify({ pin }) })
  setToken(res.token)
  return res.user
}

export async function setupFirstUser(name, pin) {
  const res = await request('/auth/setup', {
    method: 'POST',
    body: JSON.stringify({ name, pin }),
  })
  setToken(res.token)
  return res.user
}

export async function logout() {
  try {
    await request('/auth/logout', { method: 'POST' })
  } catch {
    // anche se la chiamata fallisse, cancelliamo comunque il token locale
  }
  setToken(null)
}

export function getMe() {
  return request('/auth/me')
}

// --- Utenti (gestione) ---

export function listUsers() {
  return request('/users')
}

export function createUser(name, pin) {
  return request('/users', { method: 'POST', body: JSON.stringify({ name, pin }) })
}

export function updateUser(id, patch) {
  return request(`/users/${id}`, { method: 'PATCH', body: JSON.stringify(patch) })
}

export function deleteUser(id) {
  return request(`/users/${id}`, { method: 'DELETE' })
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

export function getSuggestions(type = 'tv', opts = {}) {
  const { limit = 20, sort, minRating, yearFrom, lang, exclude } = opts
  const params = new URLSearchParams({ type, limit })
  if (sort) params.set('sort', sort)
  if (minRating) params.set('min_rating', minRating)
  if (yearFrom) params.set('year_from', yearFrom)
  if (lang) params.set('lang', lang)
  if (exclude && exclude.length) params.set('exclude', exclude.join(','))
  return request(`/tmdb/suggestions?${params.toString()}`)
}

export function dismissSuggestion(tmdbId, type = 'tv') {
  return request('/tmdb/suggestions/dismiss', {
    method: 'POST',
    body: JSON.stringify({ tmdb_id: tmdbId, media_type: type }),
  })
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
