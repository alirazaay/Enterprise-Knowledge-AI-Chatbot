import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { LoginRequest, User } from '../types/auth'
import { authStorage, getCurrentUser, login as loginRequest } from '../services/auth'
import { AuthContext } from './auth-context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => authStorage.getToken())
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(() => Boolean(authStorage.getToken()))

  const logout = useCallback(() => {
    authStorage.clearToken()
    setToken(null)
    setUser(null)
  }, [])

  useEffect(() => {
    const storedToken = authStorage.getToken()
    if (!storedToken) return

    getCurrentUser(storedToken)
      .then(setUser)
      .catch(logout)
      .finally(() => setIsLoading(false))
  }, [logout])

  const login = useCallback(async (request: LoginRequest) => {
    const response = await loginRequest(request)
    setToken(response.access_token)
    setUser(response.user)
  }, [])

  const value = useMemo(
    () => ({ user, token, isLoading, isAuthenticated: Boolean(user && token), login, logout }),
    [user, token, isLoading, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
