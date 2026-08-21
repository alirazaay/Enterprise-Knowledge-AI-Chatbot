import { api } from './api'
import type { LoginRequest, TokenResponse, User } from '../types/auth'

const tokenKey = 'enterprise-knowledge-ai.access-token'

export const authStorage = {
  getToken: () => window.localStorage.getItem(tokenKey),
  setToken: (token: string) => window.localStorage.setItem(tokenKey, token),
  clearToken: () => window.localStorage.removeItem(tokenKey),
}

export async function login(request: LoginRequest): Promise<TokenResponse> {
  const response = await api.request<TokenResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(request),
  })
  authStorage.setToken(response.access_token)
  return response
}

export function getCurrentUser(token: string): Promise<User> {
  return api.request<User>('/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
  })
}
