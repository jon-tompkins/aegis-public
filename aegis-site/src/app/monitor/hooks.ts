'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { monitorWsUrl } from './api'
import type { StreamFlagMessage, UiFlag } from './types'

export type StreamStatus = 'connecting' | 'open' | 'closed' | 'error'

export function useFlagStream(
  onFlag: (flag: UiFlag) => void,
  { enabled = true }: { enabled?: boolean } = {},
): { status: StreamStatus } {
  const [status, setStatus] = useState<StreamStatus>('connecting')
  const onFlagRef = useRef(onFlag)
  useEffect(() => {
    onFlagRef.current = onFlag
  }, [onFlag])

  useEffect(() => {
    if (!enabled) return

    let ws: WebSocket | null = null
    let retryTimer: ReturnType<typeof setTimeout> | null = null
    let closedByEffect = false
    // Backoff reconnect: start at 1s, cap at 15s.
    let backoffMs = 1000

    const connect = () => {
      setStatus('connecting')
      try {
        ws = new WebSocket(monitorWsUrl())
      } catch {
        setStatus('error')
        scheduleReconnect()
        return
      }

      ws.onopen = () => {
        backoffMs = 1000
        setStatus('open')
      }
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data) as StreamFlagMessage
          if (msg?.type === 'flag') {
            onFlagRef.current({
              id: msg.id,
              attestation: msg.attestation,
              receivedAt: Date.now(),
            })
          }
        } catch {
          // ignore malformed frames
        }
      }
      ws.onerror = () => {
        setStatus('error')
      }
      ws.onclose = () => {
        if (closedByEffect) return
        setStatus('closed')
        scheduleReconnect()
      }
    }

    const scheduleReconnect = () => {
      const delay = backoffMs
      backoffMs = Math.min(backoffMs * 2, 15_000)
      retryTimer = setTimeout(() => {
        if (!closedByEffect) connect()
      }, delay)
    }

    connect()

    return () => {
      closedByEffect = true
      if (retryTimer) clearTimeout(retryTimer)
      if (ws) {
        ws.onopen = null
        ws.onmessage = null
        ws.onerror = null
        ws.onclose = null
        ws.close()
      }
    }
  }, [enabled])

  return { status }
}

const STORAGE_KEY = 'aegis:monitor:watched'

function readStoredAddresses(): string[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return []
    return parsed.filter((x): x is string => typeof x === 'string')
  } catch {
    return []
  }
}

export function useWatchedAddresses(): {
  addresses: string[]
  add: (addr: string) => void
  remove: (addr: string) => void
  loaded: boolean
} {
  const [state, setState] = useState<{ addresses: string[]; loaded: boolean }>({
    addresses: [],
    loaded: false,
  })

  // Post-hydration read from localStorage; batched into one state update so
  // we don't flash SSR empty-state into any consumer that gates on `loaded`.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setState({ addresses: readStoredAddresses(), loaded: true })
  }, [])

  useEffect(() => {
    if (!state.loaded) return
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state.addresses))
    } catch {
      // ignore quota errors
    }
  }, [state.addresses, state.loaded])

  const add = useCallback((addr: string) => {
    const lower = addr.toLowerCase()
    setState((prev) =>
      prev.addresses.includes(lower)
        ? prev
        : { ...prev, addresses: [...prev.addresses, lower] },
    )
  }, [])

  const remove = useCallback((addr: string) => {
    const lower = addr.toLowerCase()
    setState((prev) => ({
      ...prev,
      addresses: prev.addresses.filter((a) => a !== lower),
    }))
  }, [])

  return { addresses: state.addresses, add, remove, loaded: state.loaded }
}

export function isHexAddress(value: string): boolean {
  return /^0x[0-9a-fA-F]{40}$/.test(value.trim())
}
