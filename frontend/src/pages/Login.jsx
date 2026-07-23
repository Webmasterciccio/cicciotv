import { useEffect, useState } from 'react'
import { getAuthStatus } from '../api.js'
import { useAuth } from '../auth.jsx'

const MAX_PIN = 12
const KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'back', '0', 'enter']

// Form di primo avvio: se sul server non c'e' ancora nessun utente, si crea qui
// il primo accesso (nome + PIN) e si entra subito.
function SetupForm() {
  const { setup } = useAuth()
  const [name, setName] = useState('')
  const [pin, setPin] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    if (pin.length < 4) return setError('Il PIN ha almeno 4 cifre')
    if (pin !== confirm) return setError('I due PIN non coincidono')
    setBusy(true)
    setError(null)
    try {
      await setup(name.trim(), pin)
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <form className="setup-form" onSubmit={submit}>
      <p className="login-subtitle">Primo avvio: crea il tuo accesso</p>
      <input
        type="text"
        placeholder="Nome (es. Ciccio)"
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
      />
      <input
        type="password"
        inputMode="numeric"
        placeholder="Scegli un PIN (min 4 cifre)"
        value={pin}
        onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))}
        required
      />
      <input
        type="password"
        inputMode="numeric"
        placeholder="Ripeti il PIN"
        value={confirm}
        onChange={(e) => setConfirm(e.target.value.replace(/\D/g, ''))}
        required
      />
      {error && <p className="login-message error">{error}</p>}
      <button type="submit" className="setup-submit" disabled={busy}>
        {busy ? '…' : 'Crea e accedi'}
      </button>
    </form>
  )
}

function PinPad() {
  const { login } = useAuth()
  const [pin, setPin] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function submit(value) {
    if (busy) return
    if (value.length < 4) {
      setError('Il PIN ha almeno 4 cifre')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await login(value)
      // al successo AuthProvider mostra l'app: niente altro da fare qui
    } catch (err) {
      setError(err.message || 'PIN errato')
      setPin('')
    } finally {
      setBusy(false)
    }
  }

  function press(key) {
    setError(null)
    if (key === 'back') setPin((p) => p.slice(0, -1))
    else if (key === 'enter') submit(pin)
    else setPin((p) => (p.length >= MAX_PIN ? p : p + key))
  }

  // Supporto tastiera fisica (desktop).
  useEffect(() => {
    function onKey(e) {
      if (e.key >= '0' && e.key <= '9') press(e.key)
      else if (e.key === 'Backspace') press('back')
      else if (e.key === 'Enter') press('enter')
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  return (
    <>
      <p className="login-subtitle">Inserisci il PIN per accedere</p>

      <div className="pin-dots" aria-hidden="true">
        {Array.from({ length: Math.max(4, pin.length) }).map((_, i) => (
          <span key={i} className={`pin-dot${i < pin.length ? ' filled' : ''}`} />
        ))}
      </div>

      <p className={`login-message${error ? ' error' : ''}`}>{error || ' '}</p>

      <div className="pin-pad">
        {KEYS.map((key) => {
          if (key === 'back')
            return (
              <button key={key} type="button" className="pin-key pin-key-action" onClick={() => press(key)}>
                ⌫
              </button>
            )
          if (key === 'enter')
            return (
              <button
                key={key}
                type="button"
                className="pin-key pin-key-enter"
                onClick={() => press(key)}
                disabled={busy || pin.length < 4}
              >
                {busy ? '…' : 'Entra'}
              </button>
            )
          return (
            <button key={key} type="button" className="pin-key" onClick={() => press(key)}>
              {key}
            </button>
          )
        })}
      </div>
    </>
  )
}

function Login() {
  const [needsSetup, setNeedsSetup] = useState(null) // null = ancora da sapere

  useEffect(() => {
    getAuthStatus()
      .then((s) => setNeedsSetup(!s.users_exist))
      .catch(() => setNeedsSetup(false)) // in dubbio mostriamo il login normale
  }, [])

  return (
    <div className="login-page">
      <div className="login-card">
        <h1 className="login-title">CICCIO TV</h1>
        {needsSetup === null ? (
          <p className="login-subtitle">Caricamento…</p>
        ) : needsSetup ? (
          <SetupForm />
        ) : (
          <PinPad />
        )}
      </div>
    </div>
  )
}

export default Login
