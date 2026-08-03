import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  createUser,
  deleteUser,
  getGenres,
  getSettings,
  listUsers,
  updateSettings,
  updateUser,
} from '../api.js'
import { useAuth } from '../auth.jsx'
import { MEDIA_TYPES } from '../mediaMeta.js'

// Solo i tipi con un elenco di generi a id numerici (TMDB e Jikan).
const GENRE_TYPES = MEDIA_TYPES.filter((m) => m.hasGenres)

function UsersSection() {
  const { user: me } = useAuth()
  const [users, setUsers] = useState(null)
  const [error, setError] = useState(null)
  const [newName, setNewName] = useState('')
  const [newPin, setNewPin] = useState('')

  function reload() {
    listUsers()
      .then(setUsers)
      .catch((err) => setError(err.message))
  }

  useEffect(reload, [])

  async function add(e) {
    e.preventDefault()
    setError(null)
    if (newPin.length < 4) {
      setError('Il PIN ha almeno 4 cifre')
      return
    }
    try {
      await createUser(newName.trim(), newPin)
      setNewName('')
      setNewPin('')
      reload()
    } catch (err) {
      setError(err.message)
    }
  }

  async function changePin(u) {
    const pin = window.prompt(`Nuovo PIN per ${u.name} (min 4 cifre):`)
    if (pin == null) return
    if (pin.length < 4) {
      setError('Il PIN ha almeno 4 cifre')
      return
    }
    try {
      await updateUser(u.id, { pin })
      setError(null)
    } catch (err) {
      setError(err.message)
    }
  }

  async function remove(u) {
    if (!window.confirm(`Eliminare l'utente ${u.name}?`)) return
    try {
      await deleteUser(u.id)
      reload()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <section className="users-section">
      <h2>Utenti e accesso</h2>
      <p className="hint">
        Ogni utente entra con il proprio PIN. Puoi aggiungerne altri o cambiare i PIN qui.
      </p>

      {error && <p className="error">{error}</p>}

      <ul className="users-list">
        {(users || []).map((u) => (
          <li key={u.id} className="user-row">
            <span className="user-name">
              {u.name}
              {me && u.id === me.id && <span className="hint"> (tu)</span>}
            </span>
            <span className="user-actions">
              <button type="button" onClick={() => changePin(u)}>
                Cambia PIN
              </button>
              <button type="button" className="danger" onClick={() => remove(u)}>
                Elimina
              </button>
            </span>
          </li>
        ))}
      </ul>

      <form className="user-add" onSubmit={add}>
        <input
          type="text"
          placeholder="Nome"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          required
        />
        <input
          type="password"
          inputMode="numeric"
          placeholder="PIN"
          value={newPin}
          onChange={(e) => setNewPin(e.target.value.replace(/\D/g, ''))}
          required
        />
        <button type="submit">Aggiungi utente</button>
      </form>
    </section>
  )
}

function Settings() {
  const { user } = useAuth()
  const [mediaType, setMediaType] = useState('tv')
  const [genresByType, setGenresByType] = useState({}) // { tv: [...], ... }
  const [selected, setSelected] = useState(() =>
    Object.fromEntries(GENRE_TYPES.map((m) => [m.type, new Set()])),
  )
  const [error, setError] = useState(null)
  const [savedAt, setSavedAt] = useState(false)

  // Carica le preferenze salvate (tutti i tipi con generi) una volta sola.
  useEffect(() => {
    getSettings()
      .then((s) =>
        setSelected(
          Object.fromEntries(
            GENRE_TYPES.map((m) => [m.type, new Set(s[`preferred_genres_${m.type}`] || [])]),
          ),
        ),
      )
      .catch((err) => setError(err.message))
  }, [])

  // Carica i generi del tipo selezionato (con cache).
  useEffect(() => {
    if (genresByType[mediaType]) return
    getGenres(mediaType)
      .then((list) => setGenresByType((prev) => ({ ...prev, [mediaType]: list })))
      .catch((err) => setError(err.message))
  }, [mediaType, genresByType])

  async function toggle(genreId) {
    const next = new Set(selected[mediaType])
    if (next.has(genreId)) next.delete(genreId)
    else next.add(genreId)
    const nextSelected = { ...selected, [mediaType]: next }
    setSelected(nextSelected)
    setSavedAt(false)
    try {
      await updateSettings({ [`preferred_genres_${mediaType}`]: [...next] })
      setSavedAt(true)
    } catch (err) {
      setError(err.message)
    }
  }

  if (error) return <p className="error">Errore: {error}</p>

  const genres = genresByType[mediaType]
  const selectedSet = selected[mediaType]

  return (
    <div className="settings-page">
      <h1>Impostazioni</h1>

      <section>
        <h2>Generi preferiti</h2>
        <p className="hint">
          Scegli i generi che ti piacciono, separatamente per ogni tipo: nella pagina{' '}
          <Link to="/cerca">Cerca</Link> troverai in automatico dei consigli sul prossimo titolo.
          Libri e fumetti non hanno generi da scegliere.
        </p>

        <div className="type-toggle type-toggle-scroll">
          {GENRE_TYPES.map((m) => (
            <button
              key={m.type}
              type="button"
              className={mediaType === m.type ? 'on' : ''}
              onClick={() => {
                setMediaType(m.type)
                setSavedAt(false)
              }}
            >
              {m.label}
            </button>
          ))}
        </div>

        {!genres ? (
          <p className="hint">Caricamento generi…</p>
        ) : (
          <div className="genre-picker">
            {genres.map((g) => {
              const isOn = selectedSet.has(g.id)
              return (
                <button
                  key={g.id}
                  type="button"
                  className={`genre-toggle${isOn ? ' on' : ''}`}
                  aria-pressed={isOn}
                  onClick={() => toggle(g.id)}
                >
                  {g.name}
                </button>
              )
            })}
          </div>
        )}

        <p className="settings-status hint">
          {selectedSet.size === 0
            ? 'Nessun genere selezionato per questo tipo.'
            : `${selectedSet.size} generi selezionati${savedAt ? ' · salvato ✓' : ''}`}
        </p>
      </section>

      {user?.is_admin && <UsersSection />}
    </div>
  )
}

export default Settings
