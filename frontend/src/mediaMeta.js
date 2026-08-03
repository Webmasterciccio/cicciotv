// Metadati per tipo di media: etichette, verbi e comportamenti UI in un unico
// posto, cosi' le pagine (Cerca, Libreria, Dettaglio, Consigli) restano uniformi.

export const MEDIA_TYPES = [
  { type: 'tv', label: 'Serie TV', hasGenres: true },
  { type: 'movie', label: 'Film', hasGenres: true },
  { type: 'anime', label: 'Anime', hasGenres: true },
  { type: 'manga', label: 'Manga', hasGenres: true },
  { type: 'book', label: 'Libri', hasGenres: false },
  { type: 'comic', label: 'Fumetti', hasGenres: false },
]

// Sorgente esterna associata a ogni tipo (serve per import/dismiss).
const SOURCE = {
  tv: 'tmdb',
  movie: 'tmdb',
  anime: 'jikan',
  manga: 'jikan',
  book: 'googlebooks',
  comic: 'comicvine',
}
export const sourceFor = (type) => SOURCE[type] || 'tmdb'

// Tipi che si "leggono" (manga, libri, fumetti) vs quelli che si "guardano".
const READ = new Set(['manga', 'book', 'comic'])
export const isRead = (type) => READ.has(type)
export const verb = (type) => (isRead(type) ? 'letto' : 'visto')

// Tipi con lista di unita' tracciate una a una (tabella Episode): episodi/numeri.
const UNIT_LIST = new Set(['tv', 'anime', 'comic'])
export const hasUnitList = (type) => UNIT_LIST.has(type)

// Tipi con progresso numerico (manga: capitoli, libri: pagine).
const PROGRESS = new Set(['manga', 'book'])
export const hasProgress = (type) => PROGRESS.has(type)

// Nome dell'unita' tracciata, per etichette e conteggi.
export function unitLabel(type, plural = true) {
  const map = {
    tv: ['episodio', 'episodi'],
    anime: ['episodio', 'episodi'],
    comic: ['numero', 'numeri'],
    manga: ['capitolo', 'capitoli'],
    book: ['pagina', 'pagine'],
  }
  const pair = map[type]
  return pair ? pair[plural ? 1 : 0] : ''
}

export function statusLabels(type) {
  return isRead(type)
    ? { da_vedere: 'Da leggere', in_corso: 'In lettura', vista: 'Letto' }
    : { da_vedere: 'Da vedere', in_corso: 'In corso', vista: 'Visto' }
}

// Sezioni della libreria per tipo: i film non hanno lo stato intermedio.
export function sections(type) {
  const L = statusLabels(type)
  if (type === 'movie') {
    return [
      { status: 'da_vedere', title: L.da_vedere },
      { status: 'vista', title: L.vista },
    ]
  }
  return [
    { status: 'in_corso', title: L.in_corso },
    { status: 'da_vedere', title: L.da_vedere },
    { status: 'vista', title: L.vista },
  ]
}

export function labelOf(type) {
  return MEDIA_TYPES.find((m) => m.type === type)?.label || type
}

export function searchPlaceholder(type) {
  const map = {
    tv: 'Cerca una serie TV…',
    movie: 'Cerca un film…',
    anime: 'Cerca un anime…',
    manga: 'Cerca un manga…',
    book: 'Cerca un libro…',
    comic: 'Cerca un fumetto…',
  }
  return map[type] || 'Cerca…'
}

export function suggestionsTitle(type) {
  const map = {
    tv: 'Serie consigliate per te',
    movie: 'Film consigliati per te',
    anime: 'Anime consigliati per te',
    manga: 'Manga consigliati per te',
    book: 'Libri consigliati per te',
    comic: 'Fumetti consigliati per te',
  }
  return map[type] || 'Consigliati per te'
}

export function emptyLibrary(type) {
  return isRead(type)
    ? `Non hai ancora ${labelOf(type).toLowerCase()} in libreria.`
    : `Non hai ancora ${labelOf(type).toLowerCase()} in libreria.`
}
