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
  const [mediaType, setMediaType] = useState('tv')
  const [genresByType, setGenresByType] = useState({}) // { tv: [...], movie: [...] }
  const [selected, setSelected] = useState({ tv: new Set(), movie: new Set() })
  const [error, setError] = useState(null)
  const [savedAt, setSavedAt] = useState(false)

  // Carica le preferenze salvate (entrambi i tipi) una volta sola.
  useEffect(() => {
    getSettings()
      .then((s) =>
        setSelected({
          tv: new Set(s.preferred_genres_tv),
          movie: new Set(s.preferred_genres_movie),
        }),
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
      const key = mediaType === 'movie' ? 'preferred_genres_movie' : 'preferred_genres_tv'
      await updateSettings({ [key]: [...next] })
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
          Scegli i generi che ti piacciono, separatamente per serie e film: nella pagina{' '}
          <Link to="/cerca">Cerca</Link> troverai in automatico dei consigli sul prossimo titolo
          da guardare.
        </p>

        <div className="type-toggle">
          <button
            type="button"
            className={mediaType === 'tv' ? 'on' : ''}
            onClick={() => {
              setMediaType('tv')
              setSavedAt(false)
            }}
          >
            Serie TV
          </button>
          <button
            type="button"
            className={mediaType === 'movie' ? 'on' : ''}
            onClick={() => {
              setMediaType('movie')
              setSavedAt(false)
            }}
          >
            Film
          </button>
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

      <UsersSection />
    </div>
  )
}

export default Settings
