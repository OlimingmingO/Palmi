const API_BASE = ''

function getAuthHeaders(): HeadersInit {
  const creds = localStorage.getItem('ops_credentials')
  if (!creds) return {}
  return { Authorization: `Basic ${btoa(creds)}` }
}

export function setCredentials(username: string, password: string) {
  localStorage.setItem('ops_credentials', `${username}:${password}`)
}

export function clearCredentials() {
  localStorage.removeItem('ops_credentials')
}

export function isAuthenticated(): boolean {
  return !!localStorage.getItem('ops_credentials')
}

export async function apiGet<T = unknown>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { headers: getAuthHeaders() })
  if (res.status === 401) {
    clearCredentials()
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function apiPatch<T = unknown>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'PATCH',
    headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (res.status === 401) {
    clearCredentials()
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}
