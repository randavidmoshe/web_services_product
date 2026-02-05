let isRefreshing = false
let refreshPromise: Promise<boolean> | null = null

async function refreshToken(): Promise<boolean> {
  try {
    const response = await fetch('/api/auth/refresh', {
      method: 'POST',
      credentials: 'include'
    })
    return response.ok
  } catch {
    return false
  }
}

export async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  options.credentials = 'include'

  let response = await fetch(url, options)

  if (response.status === 401 && !url.includes('/api/auth/refresh')) {
    if (!isRefreshing) {
      isRefreshing = true
      refreshPromise = refreshToken()
    }

    const refreshed = await refreshPromise
    if (isRefreshing) {
      isRefreshing = false
      refreshPromise = null
    }

    if (refreshed) {
      response = await fetch(url, options)
    } else {
      window.location.href = '/login'
    }
  }

  return response
}