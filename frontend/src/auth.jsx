import { createContext, useContext, useEffect, useState } from 'react'
import * as api from './api.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // All'avvio: se c'e' un token salvato, verifichiamo che sia ancora valido.
  useEffect(() => {
    let alive = true
    if (!api.getToken()) {
      setLoading(false)
      return
    }
    api
      .getMe()
      .then((u) => alive && setUser(u))
      .catch(() => alive && setUser(null))
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
  }, [])

  // Se un token scade durante l'uso, api.js emette questo evento: torniamo al login.
  useEffect(() => {
    const onUnauthorized = () => setUser(null)
    window.addEventListener('cicciotv:unauthorized', onUnauthorized)
    return () => window.removeEventListener('cicciotv:unauthorized', onUnauthorized)
  }, [])

  async function login(pin) {
    const u = await api.login(pin)
    setUser(u)
    return u
  }

  async function setup(name, pin) {
    const u = await api.setupFirstUser(name, pin)
    setUser(u)
    return u
  }

  async function logout() {
    await api.logout()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, setup }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth deve stare dentro <AuthProvider>')
  return ctx
}
