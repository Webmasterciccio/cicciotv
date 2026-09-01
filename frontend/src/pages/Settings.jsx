import { useEffect, useState } from 'react'
import {
  changeMyPin,
  createUser,
  deleteUser,
  exportLibrary,
  importLibrary,
  listUsers,
  updateUser,
} from '../api.js'
import { useAuth } from '../auth.jsx'

function PinSection() {
  const [currentPin, setCurrentPin] = useState('')
  const [newPin, setNewPin] = useState('')
  const [error, setError] = useState(null)
  const [done, setDone] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setError(null)
    setDone(false)
    if (newPin.length < 4) {
      setError('Il nuovo PIN ha almeno 4 cifre')
      return
    }
    try {
      await changeMyPin(currentPin, newPin)
      setCurrentPin('')
      setNewPin('')
      setDone(true)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <section className="pin-section">
      <h2>Il tuo PIN</h2>
      <p className="hint">Per cambiarlo serve conoscere quello attuale.</p>

      {error && <p className="error">{error}</p>}
      {done && <p className="hint">PIN aggiornato.</p>}

      <form className="user-add" onSubmit={submit}>
        <input
          type="password"
          inputMode="numeric"
          placeholder="PIN attuale"
          value={currentPin}
          onChange={(e) => setCurrentPin(e.target.value.replace(/\D/g, ''))}
          required
        />
        <input
          type="password"
          inputMode="numeric"
          placeholder="Nuovo PIN"
          value={newPin}
          onChange={(e) => setNewPin(e.target.value.replace(/\D/g, ''))}
          required
        />
        <button type="submit">Cambia PIN</button>
      </form>
    </section>
  )
}

function downloadJson(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function BackupSection() {
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)

  async function doExport() {
    setError(null)
    setBusy(true)
    try {
      const data = await exportLibrary()
      const today = new Date().toISOString().slice(0, 10)
      downloadJson(data, `cicciotv-backup-${today}.json`)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function doImport(e) {
    const file = e.target.files?.[0]
    e.target.value = '' // permette di reimportare lo stesso file una seconda volta
    if (!file) return
    setError(null)
    setResult(null)
    setBusy(true)
    try {
      const text = await file.text()
      const data = JSON.parse(text)
      const res = await importLibrary(data)
      setResult(res)
    } catch (err) {
      setError(err.message || 'File non valido')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="backup-section">
      <h2>Backup della libreria</h2>
      <p className="hint">
        Esporta i tuoi titoli, gli episodi/volumi visti e le preferenze in un file, da
        conservare o reimportare qui o su un'altra installazione. I titoli gia' presenti
        in libreria vengono lasciati come sono: l'importazione aggiunge solo quelli mancanti.
      </p>

      {error && <p className="error">{error}</p>}
      {result && (
        <p className="hint">
          Importazione completata: {result.imported} aggiunti, {result.skipped} gia' presenti.
        </p>
      )}

      <div className="backup-actions">
        <button type="button" onClick={doExport} disabled={busy}>
          Esporta libreria
        </button>
        <label className="button-like">
          Importa libreria
          <input type="file" accept="application/json" onChange={doImport} disabled={busy} hidden />
        </label>
      </div>
    </section>
  )
}

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

      <PinSection />
      <BackupSection />
      {user?.is_admin && <UsersSection />}
    </div>
  )
}

export default Settings
