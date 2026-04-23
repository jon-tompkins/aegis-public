// Mirrors aegis-monitor/src/aegis_monitor/schemas.py — keep in sync.

export type Severity = 'low' | 'medium' | 'high' | 'critical'

export interface Attestation {
  tx_hash: string
  monitored_address: string
  rule_id: string
  rule_version: string
  severity: Severity
  reason_human: string
  reason_structured: Record<string, unknown>
  agent_id: string
  ts_ms: number
  sig: string
}

export interface FlagResponse {
  id: number
  attestation: Attestation
  created_at: string
}

export interface FlagsPage {
  flags: FlagResponse[]
  next_before_id: number | null
}

export interface MonitorItem {
  address: string
  active: boolean
}

export interface MonitorList {
  addresses: string[]
}

export interface StreamFlagMessage {
  type: 'flag'
  id: number
  attestation: Attestation
}

export interface UiFlag {
  id: number
  attestation: Attestation
  receivedAt: number
}
