'use client'

import Link from 'next/link'
import { useCallback, useEffect, useMemo, useState } from 'react'
import ShieldIcon from '../components/ShieldIcon'
import {
  addMonitored,
  fetchFlags,
  fetchReady,
  listMonitored,
  MONITOR_HTTP_URL,
  removeMonitored,
} from './api'
import { isHexAddress, useFlagStream, useWatchedAddresses } from './hooks'
import type { Severity, UiFlag } from './types'

// ----- top bar -----

type EthereumProvider = {
  request: (args: { method: string; params?: unknown[] }) => Promise<unknown>
  on?: (event: string, handler: (...args: unknown[]) => void) => void
  removeListener?: (event: string, handler: (...args: unknown[]) => void) => void
}

function getEthereum(): EthereumProvider | null {
  if (typeof window === 'undefined') return null
  const w = window as unknown as { ethereum?: EthereumProvider }
  return w.ethereum ?? null
}

function shortAddr(addr: string): string {
  if (addr.length < 10) return addr
  return `${addr.slice(0, 6)}…${addr.slice(-4)}`
}

function WalletConnect({ onAddress }: { onAddress: (addr: string) => void }) {
  const [connected, setConnected] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const eth = useMemo(() => getEthereum(), [])

  useEffect(() => {
    if (!eth) return
    // silent: if wallet is already unlocked + authorised, pick up the address
    eth
      .request({ method: 'eth_accounts' })
      .then((accs) => {
        const list = accs as string[]
        if (list && list[0]) setConnected(list[0].toLowerCase())
      })
      .catch(() => {})
  }, [eth])

  const connect = useCallback(async () => {
    if (!eth) return
    setBusy(true)
    setErr(null)
    try {
      const accs = (await eth.request({ method: 'eth_requestAccounts' })) as string[]
      const addr = accs?.[0]?.toLowerCase() ?? null
      setConnected(addr)
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'wallet connect failed')
    } finally {
      setBusy(false)
    }
  }, [eth])

  if (!eth) {
    return (
      <span className="text-xs text-[#4a5a7a] font-['JetBrains_Mono']">
        no wallet detected
      </span>
    )
  }

  if (connected) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-xs font-['JetBrains_Mono'] text-[#c8d4e8]">
          {shortAddr(connected)}
        </span>
        <button
          onClick={() => onAddress(connected)}
          className="text-xs px-3 py-1.5 rounded-md border border-[#1a2a4a] bg-[#0d1525] text-[#00d4ff] hover:border-[#00d4ff] transition-colors font-['JetBrains_Mono']"
        >
          Watch my address
        </button>
      </div>
    )
  }

  return (
    <button
      onClick={connect}
      disabled={busy}
      className="text-xs px-3 py-1.5 rounded-md border border-[#1a2a4a] bg-[#0d1525] text-[#c8d4e8] hover:border-[#00d4ff] hover:text-[#00d4ff] transition-colors font-['JetBrains_Mono'] disabled:opacity-50"
      title={err ?? undefined}
    >
      {busy ? 'connecting…' : 'Connect wallet'}
    </button>
  )
}

function Nav({ onWalletAddress }: { onWalletAddress: (addr: string) => void }) {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-[#1a2a4a] bg-[#050810]/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 h-16 flex items-center justify-between gap-4">
        <Link href="/" className="flex items-center gap-3">
          <ShieldIcon className="w-7 h-7 text-[#00d4ff]" />
          <span className="font-['Space_Grotesk'] font-bold text-lg text-white">Aegis</span>
          <span className="text-sm text-[#4a5a7a] font-['JetBrains_Mono']">/ monitor</span>
        </Link>
        <div className="flex items-center gap-4">
          <WalletConnect onAddress={onWalletAddress} />
        </div>
      </div>
    </nav>
  )
}

// ----- left panel: watched addresses -----

function WatchedPanel({
  addresses,
  onAdd,
  onRemove,
  backendSyncError,
}: {
  addresses: string[]
  onAdd: (addr: string) => void
  onRemove: (addr: string) => void
  backendSyncError: string | null
}) {
  const [input, setInput] = useState('')
  const [err, setErr] = useState<string | null>(null)

  const submit = (e?: React.FormEvent) => {
    e?.preventDefault()
    const trimmed = input.trim()
    if (!trimmed) return
    if (!isHexAddress(trimmed)) {
      setErr('0x-prefixed 40-hex-char address required')
      return
    }
    setErr(null)
    onAdd(trimmed.toLowerCase())
    setInput('')
  }

  return (
    <aside className="lg:sticky lg:top-20 lg:self-start lg:h-[calc(100vh-6rem)] flex flex-col gap-4">
      <div className="p-4 rounded-xl bg-[#0d1525] border border-[#1a2a4a]">
        <h2 className="text-sm font-['Space_Grotesk'] font-semibold text-white mb-3">
          Watched addresses
        </h2>
        <form onSubmit={submit} className="flex flex-col gap-2">
          <input
            value={input}
            onChange={(e) => {
              setInput(e.target.value)
              if (err) setErr(null)
            }}
            placeholder="0x…"
            spellCheck={false}
            className="w-full px-3 py-2 rounded-md bg-[#050810] border border-[#1a2a4a] text-sm font-['JetBrains_Mono'] text-[#c8d4e8] placeholder-[#4a5a7a] focus:border-[#00d4ff] focus:outline-none"
          />
          <button
            type="submit"
            className="px-3 py-2 rounded-md bg-[#00d4ff] text-[#050810] text-sm font-['Space_Grotesk'] font-semibold hover:shadow-[0_0_20px_rgba(0,212,255,0.35)] transition-shadow"
          >
            Add address
          </button>
          {err && <div className="text-xs text-[#ff4455] font-['JetBrains_Mono']">{err}</div>}
        </form>
      </div>

      <div className="p-4 rounded-xl bg-[#0d1525] border border-[#1a2a4a] flex-1 overflow-y-auto">
        {backendSyncError && (
          <div className="mb-3 p-2 rounded-md border border-[#ff4455]/30 bg-[#ff4455]/5 text-xs font-['JetBrains_Mono'] text-[#ff4455]">
            {backendSyncError}
          </div>
        )}
        {addresses.length === 0 ? (
          <div className="text-xs text-[#4a5a7a] font-['JetBrains_Mono']">
            No addresses watched yet. Paste one above or connect a wallet.
          </div>
        ) : (
          <ul className="space-y-2">
            {addresses.map((addr) => (
              <li
                key={addr}
                className="flex items-center justify-between gap-2 p-2 rounded-md border border-[#1a2a4a] bg-[#050810]"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="w-2 h-2 rounded-full bg-[#00cc88] animate-pulse shrink-0" />
                  <code
                    title={addr}
                    className="text-xs font-['JetBrains_Mono'] text-[#c8d4e8] truncate"
                  >
                    {shortAddr(addr)}
                  </code>
                </div>
                <button
                  onClick={() => onRemove(addr)}
                  aria-label={`Remove ${addr}`}
                  className="text-xs px-2 py-1 rounded text-[#4a5a7a] hover:text-[#ff4455] hover:bg-[#ff4455]/10 transition-colors font-['JetBrains_Mono']"
                >
                  remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  )
}

// ----- right panel: flag feed -----

function severityStyle(sev: Severity): string {
  switch (sev) {
    case 'critical':
      return 'border-[#ff4455] bg-[#ff4455]/10 text-[#ff4455]'
    case 'high':
      return 'border-[#ff4455]/70 bg-[#ff4455]/5 text-[#ff4455]'
    case 'medium':
      return 'border-[#ffd700]/70 bg-[#ffd700]/5 text-[#ffd700]'
    case 'low':
      return 'border-[#00d4ff]/60 bg-[#00d4ff]/5 text-[#00d4ff]'
  }
}

function formatTs(ms: number): string {
  const d = new Date(ms)
  return d.toISOString().replace('T', ' ').replace('Z', ' UTC')
}

function FlagCard({ flag }: { flag: UiFlag }) {
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const { attestation: att } = flag
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(att.sig)
      setCopied(true)
      setTimeout(() => setCopied(false), 1400)
    } catch {
      // ignore
    }
  }
  const etherscan = `https://etherscan.io/tx/${att.tx_hash}`

  return (
    <article
      className={`rounded-xl border ${severityStyle(att.severity)} p-4 space-y-3 animate-fade-up`}
    >
      <header className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={`text-xs font-['JetBrains_Mono'] uppercase tracking-wide px-2 py-0.5 rounded border ${severityStyle(att.severity)}`}
          >
            {att.severity}
          </span>
          <span className="text-xs font-['JetBrains_Mono'] text-[#c8d4e8]">
            {att.rule_id}
          </span>
          <span className="text-xs font-['JetBrains_Mono'] text-[#4a5a7a]">
            {att.rule_version}
          </span>
        </div>
        <span className="text-xs font-['JetBrains_Mono'] text-[#4a5a7a]">
          {formatTs(att.ts_ms)}
        </span>
      </header>

      <p className="text-sm text-[#c8d4e8] leading-relaxed">{att.reason_human}</p>

      <div className="flex items-center gap-3 flex-wrap text-xs font-['JetBrains_Mono']">
        <span className="text-[#4a5a7a]">addr</span>
        <code className="text-[#c8d4e8]" title={att.monitored_address}>
          {shortAddr(att.monitored_address)}
        </code>
        <span className="text-[#4a5a7a]">tx</span>
        <a
          href={etherscan}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[#00d4ff] hover:underline"
          title={att.tx_hash}
        >
          {shortAddr(att.tx_hash)} ↗
        </a>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => setOpen((v) => !v)}
          className="text-xs px-2 py-1 rounded-md border border-[#1a2a4a] bg-[#0d1525] text-[#c8d4e8] hover:border-[#00d4ff] hover:text-[#00d4ff] transition-colors font-['JetBrains_Mono']"
        >
          {open ? 'hide attestation' : 'show attestation'}
        </button>
        <button
          onClick={copy}
          className="text-xs px-2 py-1 rounded-md border border-[#1a2a4a] bg-[#0d1525] text-[#c8d4e8] hover:border-[#00d4ff] hover:text-[#00d4ff] transition-colors font-['JetBrains_Mono']"
        >
          {copied ? 'copied ✓' : 'copy signature'}
        </button>
        <span className="text-xs font-['JetBrains_Mono'] text-[#4a5a7a]">
          agent {att.agent_id}
        </span>
      </div>

      {open && (
        <pre className="text-xs font-['JetBrains_Mono'] text-[#c8d4e8] bg-[#050810] border border-[#1a2a4a] rounded-md p-3 overflow-x-auto">
          {JSON.stringify(att, null, 2)}
        </pre>
      )}
    </article>
  )
}

// ----- demo helper -----

function DemoHelper() {
  const [open, setOpen] = useState(false)
  return (
    <section className="mt-8 rounded-xl border border-[#1a2a4a] bg-[#0d1525]">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full text-left px-5 py-4 flex items-center justify-between gap-4"
      >
        <div>
          <h3 className="text-sm font-['Space_Grotesk'] font-semibold text-white">
            How to trigger a demo flag
          </h3>
          <p className="text-xs text-[#4a5a7a] mt-1">
            Step-by-step to produce a Tier 1 hit against a watched address.
          </p>
        </div>
        <span className="text-xs font-['JetBrains_Mono'] text-[#00d4ff] shrink-0">
          {open ? '− hide' : '+ show'}
        </span>
      </button>
      {open && (
        <div className="px-5 pb-5 space-y-3 text-sm text-[#c8d4e8] leading-relaxed">
          <ol className="list-decimal pl-5 space-y-2">
            <li>
              Watch the EOA you control with either the{' '}
              <strong>Connect wallet</strong> shortcut or by pasting the address in the left
              panel.
            </li>
            <li>
              From that EOA on mainnet (or the network the agent subscribes to), call{' '}
              <code className="text-[#00d4ff]">approve(spender, uint256.max)</code> on any
              ERC-20 where <em>spender</em> is an EOA (no bytecode). That trips{' '}
              <code className="text-[#00d4ff]">t1.approve_to_eoa</code>.
            </li>
            <li>
              Alternatively, approve an unlimited allowance to a contract to trigger{' '}
              <code className="text-[#00d4ff]">t1.unlimited_approval</code>.
            </li>
            <li>
              Watch the feed on the right — the flag should arrive within a second or two of
              your tx hitting the mempool, well before it mines.
            </li>
          </ol>
          <p className="text-xs text-[#4a5a7a] font-['JetBrains_Mono']">
            Tip: use a throwaway EOA with a small ETH balance. No funds are at risk from the
            approval until a <code>transferFrom</code> fires — which is itself flagged by{' '}
            <code>t1.transfer_from_unauthorized</code>.
          </p>
        </div>
      )}
    </section>
  )
}

// ----- page -----

const MAX_FLAGS_RETAINED = 200

export default function MonitorPage() {
  const { addresses, add: addLocal, remove: removeLocal, loaded } = useWatchedAddresses()
  const [flags, setFlags] = useState<UiFlag[]>([])
  const [ready, setReady] = useState<boolean | null>(null)
  const [backendSyncError, setBackendSyncError] = useState<string | null>(null)

  const pushFlag = useCallback((flag: UiFlag) => {
    setFlags((prev) => {
      if (prev.some((f) => f.id === flag.id)) return prev
      const next = [flag, ...prev]
      return next.length > MAX_FLAGS_RETAINED ? next.slice(0, MAX_FLAGS_RETAINED) : next
    })
  }, [])

  const { status } = useFlagStream(pushFlag, { enabled: loaded })

  // readiness probe — informational, doesn't block UI
  useEffect(() => {
    let cancelled = false
    fetchReady().then((ok) => {
      if (!cancelled) setReady(ok)
    })
    const iv = setInterval(() => {
      fetchReady().then((ok) => {
        if (!cancelled) setReady(ok)
      })
    }, 15_000)
    return () => {
      cancelled = true
      clearInterval(iv)
    }
  }, [])

  // pull historical flags on mount so the feed isn't empty for returning users
  useEffect(() => {
    if (!loaded) return
    let cancelled = false
    fetchFlags(undefined, 50)
      .then((page) => {
        if (cancelled) return
        const ui: UiFlag[] = page.flags.map((f) => ({
          id: f.id,
          attestation: f.attestation,
          receivedAt: Date.parse(f.created_at),
        }))
        setFlags((prev) => {
          const seen = new Set(prev.map((f) => f.id))
          const merged = [...prev, ...ui.filter((f) => !seen.has(f.id))]
          merged.sort((a, b) => b.id - a.id)
          return merged.slice(0, MAX_FLAGS_RETAINED)
        })
      })
      .catch(() => {
        // backend may be down during dev; WS hook surfaces the live status
      })
    return () => {
      cancelled = true
    }
  }, [loaded])

  // sync local watched list to the backend monitor set
  const syncAdd = useCallback(
    async (addr: string) => {
      addLocal(addr)
      try {
        await addMonitored(addr)
        setBackendSyncError(null)
      } catch (e) {
        setBackendSyncError(
          `Agent sync failed: ${e instanceof Error ? e.message : 'unknown'}. Address is tracked locally; re-add once the agent is reachable.`,
        )
      }
    },
    [addLocal],
  )

  const syncRemove = useCallback(
    async (addr: string) => {
      removeLocal(addr)
      try {
        await removeMonitored(addr)
        setBackendSyncError(null)
      } catch {
        // silent: local removal still happened
      }
    },
    [removeLocal],
  )

  // reconcile: on first backend contact, ensure every locally-remembered
  // address is registered with the agent.
  useEffect(() => {
    if (!loaded) return
    listMonitored()
      .then((list) => {
        const already = new Set(list.addresses.map((a) => a.toLowerCase()))
        for (const a of addresses) {
          if (!already.has(a)) {
            addMonitored(a).catch(() => {})
          }
        }
      })
      .catch(() => {})
    // only run once per page load
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded])

  return (
    <main className="min-h-screen bg-[#050810] dot-grid">
      <Nav onWalletAddress={syncAdd} />

      <div className="pt-20 pb-12 px-6 sm:px-8 max-w-7xl mx-auto">
        <header className="mb-6 flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-2xl sm:text-3xl font-['Space_Grotesk'] font-bold text-white">
              Live flag feed
            </h1>
            <p className="text-sm text-[#4a5a7a] mt-1 max-w-2xl">
              Watch addresses. When the agent screens a pending tx and a Tier 1 rule fires, a
              signed attestation lands here in real time. Open any card to inspect the
              canonical JSON.
            </p>
          </div>
          <div className="flex flex-col sm:items-end gap-1 text-xs font-['JetBrains_Mono']">
            <StatusRow label="stream" state={statusToState(status)} detail={status} />
            <StatusRow
              label="agent"
              state={ready === null ? 'pending' : ready ? 'ok' : 'error'}
              detail={ready === null ? 'probing…' : ready ? 'ready' : 'unreachable'}
            />
            <span className="text-[#4a5a7a]">
              <span className="text-[#4a5a7a]">api</span>{' '}
              <code className="text-[#c8d4e8]">{MONITOR_HTTP_URL}</code>
            </span>
          </div>
        </header>

        <div className="grid lg:grid-cols-[280px_1fr] gap-6">
          <WatchedPanel
            addresses={addresses}
            onAdd={syncAdd}
            onRemove={syncRemove}
            backendSyncError={backendSyncError}
          />

          <section className="min-w-0">
            {flags.length === 0 ? (
              <div className="rounded-xl border border-[#1a2a4a] bg-[#0d1525] p-10 text-center">
                <p className="text-sm text-[#c8d4e8]">
                  Feed is quiet. Add an address and wait for a flagged tx — or follow the demo
                  helper below.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {flags.map((f) => (
                  <FlagCard key={f.id} flag={f} />
                ))}
                {flags.length >= MAX_FLAGS_RETAINED && (
                  <p className="text-xs text-center text-[#4a5a7a] font-['JetBrains_Mono'] py-2">
                    showing most recent {MAX_FLAGS_RETAINED} — older flags available via{' '}
                    <code className="text-[#c8d4e8]">GET /flags</code>
                  </p>
                )}
              </div>
            )}

            <DemoHelper />
          </section>
        </div>
      </div>
    </main>
  )
}

function statusToState(s: ReturnType<typeof useFlagStream>['status']): StatusState {
  switch (s) {
    case 'open':
      return 'ok'
    case 'connecting':
      return 'pending'
    case 'closed':
    case 'error':
      return 'error'
  }
}

type StatusState = 'ok' | 'pending' | 'error'

function StatusRow({
  label,
  state,
  detail,
}: {
  label: string
  state: StatusState
  detail: string
}) {
  const color =
    state === 'ok' ? 'bg-[#00cc88]' : state === 'pending' ? 'bg-[#ffd700]' : 'bg-[#ff4455]'
  return (
    <span className="flex items-center gap-2">
      <span className={`w-2 h-2 rounded-full ${color} ${state === 'pending' ? 'animate-pulse' : ''}`} />
      <span className="text-[#4a5a7a]">{label}</span>
      <span className="text-[#c8d4e8]">{detail}</span>
    </span>
  )
}
