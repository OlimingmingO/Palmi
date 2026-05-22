const API_BASE = ''

export async function apiPost<T = unknown>(path: string, body: unknown): Promise<T> {
  const token = localStorage.getItem('config_token')
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'X-Config-Token': token } : {}),
    },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => null)
    const detail = data?.detail
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map((d: any) => d.msg).join('; ')
        : `API error: ${res.status}`
    throw new Error(message)
  }
  return res.json()
}

export async function apiGet<T = unknown>(path: string): Promise<T> {
  const token = localStorage.getItem('config_token')
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      ...(token ? { 'X-Config-Token': token } : {}),
    },
  })
  if (!res.ok) {
    const data = await res.json().catch(() => null)
    const detail = data?.detail
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map((d: any) => d.msg).join('; ')
        : `API error: ${res.status}`
    throw new Error(message)
  }
  return res.json()
}
