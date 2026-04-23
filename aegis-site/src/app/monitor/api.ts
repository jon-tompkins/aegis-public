import type { FlagsPage, MonitorItem, MonitorList } from './types'

// Configured at build time via NEXT_PUBLIC_AEGIS_MONITOR_URL; defaults to
// localhost so `npm run dev` against a locally-running agent just works.
export const MONITOR_HTTP_URL =
  process.env.NEXT_PUBLIC_AEGIS_MONITOR_URL ?? 'http://localhost:8000'

export function monitorWsUrl(): string {
  const base = MONITOR_HTTP_URL
  if (base.startsWith('https://')) return 'wss://' + base.slice('https://'.length) + '/stream'
  if (base.startsWith('http://')) return 'ws://' + base.slice('http://'.length) + '/stream'
  return base + '/stream'
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(MONITOR_HTTP_URL + path, init)
  if (!res.ok) {
    let detail: string | undefined
    try {
      const body = (await res.json()) as { detail?: string }
      detail = body?.detail
    } catch {
      // non-JSON error body
    }
    throw new Error(`${res.status} ${res.statusText}${detail ? ` — ${detail}` : ''}`)
  }
  return (await res.json()) as T
}

export async function listMonitored(): Promise<MonitorList> {
  return request<MonitorList>('/monitor')
}

export async function addMonitored(address: string): Promise<MonitorItem> {
  return request<MonitorItem>('/monitor', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ address }),
  })
}

export async function removeMonitored(address: string): Promise<MonitorItem> {
  return request<MonitorItem>(`/monitor/${address}`, { method: 'DELETE' })
}

export async function fetchFlags(address?: string, limit = 100): Promise<FlagsPage> {
  const params = new URLSearchParams()
  if (address) params.set('address', address)
  params.set('limit', String(limit))
  return request<FlagsPage>('/flags?' + params.toString())
}

export async function fetchReady(): Promise<boolean> {
  try {
    const res = await fetch(MONITOR_HTTP_URL + '/ready')
    return res.ok
  } catch {
    return false
  }
}
