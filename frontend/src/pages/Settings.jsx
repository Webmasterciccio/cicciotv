import { useEffect, useState } from 'react'
import { createUser, deleteUser, listUsers, updateUser } from '../api.js'
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
  const { user } = useAuth()

  return (
    <div className="settings-page">
      <h1>Impostazioni</h1>

      {user?.is_admin && <UsersSection />}
    </div>
  )
}

export default Settings
