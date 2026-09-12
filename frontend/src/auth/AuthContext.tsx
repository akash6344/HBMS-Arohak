import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { api } from '../lib/api'
import { tokenStorage } from '../lib/storage'
import type { AuthenticatedPrincipal, Role } from '../lib/types'

interface AuthContextValue {
  principal: AuthenticatedPrincipal | null
  loading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<AuthenticatedPrincipal>
  register: (name: string, email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  hasRole: (...roles: Role[]) => boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [principal, setPrincipal] = useState<AuthenticatedPrincipal | null>(null)
  const [loading, setLoading] = useState(true)

  const hydrate = useCallback(async () => {
    if (!tokenStorage.getAccess()) {
      setPrincipal(null)
      setLoading(false)
      return
    }
    try {
      const me = await api.me()
      setPrincipal(me)
    } catch {
      tokenStorage.clear()
      setPrincipal(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void hydrate()
  }, [hydrate])

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await api.login({ email, password })
    tokenStorage.setTokens(tokens.access_token, tokens.refresh_token)
    const me = await api.me()
    setPrincipal(me)
    return me
  }, [])

  const register = useCallback(async (name: string, email: string, password: string) => {
    await api.register({ name, email, password })
  }, [])

  const logout = useCallback(async () => {
    const refresh = tokenStorage.getRefresh()
    if (refresh) {
      try {
        await api.logout(refresh)
      } catch {
        // ignore logout network failures
      }
    }
    tokenStorage.clear()
    setPrincipal(null)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      principal,
      loading,
      isAuthenticated: Boolean(principal),
      login,
      register,
      logout,
      hasRole: (...roles: Role[]) => Boolean(principal && roles.includes(principal.role)),
    }),
    [principal, loading, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
