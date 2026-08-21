const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export const api = {
  baseUrl: apiBaseUrl.replace(/\/$/, ''),
  healthUrl: `${apiBaseUrl.replace(/\/$/, '')}/health`,
  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(`${apiBaseUrl.replace(/\/$/, '')}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...init.headers,
      },
    })

    if (!response.ok) {
      let message = 'The request could not be completed.'
      try {
        const body = (await response.json()) as { detail?: string }
        if (body.detail) message = body.detail
      } catch {
        // Keep a safe generic message when the backend response is not JSON.
      }
      throw new ApiError(message, response.status)
    }

    return (await response.json()) as T
  },
}

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message)
    this.name = 'ApiError'
  }
}
