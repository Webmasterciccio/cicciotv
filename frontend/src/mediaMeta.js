// Metadati per tipo di media: etichette, verbi e comportamenti UI in un unico
// posto, cosi' le pagine (Cerca, Libreria, Dettaglio, Consigli) restano uniformi.

// L'anime non e' una sezione a se': confluisce in "Serie TV" (con fallback su
// AniList in ricerca quando TMDB non ha il titolo).
export const MEDIA_TYPES = [
  { type: 'tv', label: 'Serie TV' },
  { type: 'movie', label: 'Film' },
  { type: 'manga', label: 'Manga' },
  { type: 'book', label: 'Libri' },
  { type: 'comic', label: 'Fumetti' },
]

// Sorgente esterna associata a ogni tipo (serve per import/dismiss).
const SOURCE = {
  tv: 'tmdb',
  movie: 'tmdb',
  manga: 'anilist',
  book: 'googlebooks',
  comic: 'comicvine',
}
export const sourceFor = (type) => SOURCE[type] || 'tmdb'

// Opzioni dei filtri di voto/periodo, condivise da Ricerca e Consigliati.
export const RATING_OPTIONS = [
  { value: '', label: 'Voto: tutti' },
  { value: '6', label: '★ 6+' },
  { value: '7', label: '★ 7+' },
  { value: '8', label: '★ 8+' },
]
export const PERIOD_OPTIONS = [
  { value: '', label: 'Periodo: tutto' },
  { value: '5', label: 'Ultimi 5 anni' },
  { value: '10', label: 'Ultimi 10 anni' },
  { value: '2000', label: 'Dal 2000' },
]

// La lingua originale ha senso solo per serie/film (TMDB): per gli altri tipi
// i titoli sono in giapponese/inglese, quindi il filtro "Solo IT" non serve.
export const langFilterAvailable = (type) => type === 'tv' || type === 'movie'

// Tipi che si "leggono" (manga, libri, fumetti) vs quelli che si "guardano".
const READ = new Set(['manga', 'book', 'comic'])
export const isRead = (type) => READ.has(type)
export const verb = (type) => (isRead(type) ? 'letto' : 'visto')

// Tipi con lista di unita' tracciate una a una (tabella Episode): episodi/numeri.
const UNIT_LIST = new Set(['tv', 'comic'])
export const hasUnitList = (type) => UNIT_LIST.has(type)

// Tipi con progresso numerico (manga: capitoli, libri: pagine).
const PROGRESS = new Set(['manga', 'book'])
export const hasProgress = (type) => PROGRESS.has(type)

// Nome dell'unita' tracciata, per etichette e conteggi.
export function unitLabel(type, plural = true) {
  const map = {
    tv: ['episodio', 'episodi'],
    comic: ['numero', 'numeri'],
    manga: ['volume', 'volumi'],
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
    tv: 'Cerca una serie TV o un anime…',
    movie: 'Cerca un film…',
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
