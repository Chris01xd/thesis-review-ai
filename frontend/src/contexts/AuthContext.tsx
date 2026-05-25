import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import type { User } from '../types'
import { login as apiLogin } from '../api'

interface AuthState {
  user: User | null
  token: string | null
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

function loadFromStorage(): AuthState {
  try {
    const user = localStorage.getItem('tr_user')
    const token = localStorage.getItem('tr_token')
    return { user: user ? JSON.parse(user) : null, token }
  } catch {
    return { user: null, token: null }
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(loadFromStorage)

  const login = useCallback(async (email: string, password: string) => {
    const data = await apiLogin(email, password)
    localStorage.setItem('tr_token', data.token)
    localStorage.setItem('tr_user', JSON.stringify(data.user))
    setState({ user: data.user, token: data.token })
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('tr_token')
    localStorage.removeItem('tr_user')
    setState({ user: null, token: null })
  }, [])

  return (
    <AuthContext.Provider value={{ ...state, login, logout, isAuthenticated: !!state.user }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
