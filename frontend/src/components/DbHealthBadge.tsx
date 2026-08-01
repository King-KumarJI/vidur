import { useEffect, useState } from 'react'
import { getDatabaseHealth } from '../services/apiClient'
import type { DatabaseHealthResponse } from '../services/types'

const POLL_INTERVAL_MS = 30_000

export function DbHealthBadge() {
  const [health, setHealth] = useState<DatabaseHealthResponse | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function poll() {
      try {
        const result = await getDatabaseHealth()
        if (!cancelled) {
          setHealth(result)
          setFailed(false)
        }
      } catch {
        if (!cancelled) setFailed(true)
      }
    }

    void poll()
    const interval = window.setInterval(() => void poll(), POLL_INTERVAL_MS)
    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [])

  const healthy = health?.healthy ?? false
  const color = failed || !health ? 'var(--color-vidur-text-muted)' : healthy ? 'var(--color-vidur-good)' : 'var(--color-vidur-bad)'
  const label = failed || !health ? 'Backend unreachable' : healthy ? 'Databases healthy' : 'Database issue'

  return (
    <div className="flex items-center gap-2 rounded-md border border-vidur-border bg-vidur-surface-raised px-3 py-1.5 text-xs text-vidur-text-muted" title={
      health ? `Mongo: ${health.mongodb_connected ? 'up' : 'down'} · Chroma: ${health.chromadb_connected ? 'up' : 'down'}` : undefined
    }>
      <span className="h-2 w-2 rounded-full" style={{ background: color }} />
      {label}
    </div>
  )
}
