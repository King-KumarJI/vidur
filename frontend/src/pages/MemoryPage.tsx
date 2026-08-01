import { useState } from 'react'
import { HealthScoreTrendChart } from '../components/HealthScoreTrendChart'
import { Card, EmptyState, ErrorBanner, PrimaryButton, Spinner, TextInput } from '../components/ui'
import { useProject } from '../context/ProjectContext'
import { getHealthScoreTrend, getMemoryHistory, recallMemory } from '../services/apiClient'
import type { MemoryRecallMatchResponse, MemoryRecordResponse } from '../services/types'

// Mirrors backend/app/memory/enums.py MemoryRecordType.
const RECORD_TYPES = ['inspection', 'ai_reasoning', 'nlp', 'ml_prediction', 'visual_regression'] as const

export function MemoryPage() {
  const { projectId } = useProject()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-vidur-text">Memory / History</h1>
        <p className="text-sm text-vidur-text-muted">
          Recall VIDUR's own recorded analysis history for the active project — semantic recall,
          chronological history, and health-score trend.
        </p>
      </div>

      {!projectId ? (
        <ErrorBanner error={new Error('Select an active project on the Projects page to browse its memory.')} />
      ) : (
        <>
          <TrendSection />
          <RecallSection />
          <HistorySection />
        </>
      )}
    </div>
  )
}

function TrendSection() {
  const [recordTypes, setRecordTypes] = useState<string[]>([])
  const [scores, setScores] = useState<number[] | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(false)

  function toggleType(type: string) {
    setRecordTypes((prev) => (prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]))
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const result = await getHealthScoreTrend(recordTypes.length > 0 ? recordTypes : undefined)
      setScores(result.health_scores)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card title="Health Score Trend">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        {RECORD_TYPES.map((type) => (
          <button
            key={type}
            type="button"
            onClick={() => toggleType(type)}
            className={`rounded-full border px-3 py-1 text-xs ${
              recordTypes.includes(type)
                ? 'border-vidur-accent bg-vidur-accent-muted text-vidur-text'
                : 'border-vidur-border text-vidur-text-muted hover:border-vidur-accent'
            }`}
          >
            {type}
          </button>
        ))}
        <PrimaryButton onClick={() => void load()} disabled={loading}>
          {loading ? 'Loading…' : 'Load Trend'}
        </PrimaryButton>
      </div>
      <ErrorBanner error={error} />
      {loading ? <Spinner /> : scores ? <HealthScoreTrendChart healthScores={scores} /> : (
        <EmptyState message="Choose optional record types and load the trend." />
      )}
    </Card>
  )
}

function RecallSection() {
  const [queryText, setQueryText] = useState('')
  const [topK, setTopK] = useState('5')
  const [recordType, setRecordType] = useState('')
  const [matches, setMatches] = useState<MemoryRecallMatchResponse[] | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit() {
    if (!queryText.trim()) return
    setLoading(true)
    setError(null)
    try {
      const result = await recallMemory(queryText.trim(), Number(topK) || 5, recordType || undefined)
      setMatches(result)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card title="Semantic Recall">
      <div className="flex flex-wrap gap-2">
        <TextInput value={queryText} onChange={setQueryText} placeholder="Query text" className="min-w-64 flex-1" />
        <TextInput value={topK} onChange={setTopK} placeholder="top_k" className="w-20" />
        <select
          value={recordType}
          onChange={(e) => setRecordType(e.target.value)}
          className="rounded-md border border-vidur-border bg-vidur-surface-raised px-3 py-2 text-sm text-vidur-text focus:border-vidur-accent focus:outline-none"
        >
          <option value="">Any record type</option>
          {RECORD_TYPES.map((type) => (
            <option key={type} value={type}>{type}</option>
          ))}
        </select>
        <PrimaryButton onClick={() => void handleSubmit()} disabled={loading || !queryText.trim()}>
          {loading ? 'Recalling…' : 'Recall'}
        </PrimaryButton>
      </div>
      <ErrorBanner error={error} />
      {matches ? (
        matches.length === 0 ? (
          <EmptyState message="No matching records." />
        ) : (
          <ul className="mt-3 space-y-2">
            {matches.map((match) => (
              <MemoryRecordItem key={match.record.record_id} record={match.record} similarity={match.similarity_score} />
            ))}
          </ul>
        )
      ) : null}
    </Card>
  )
}

function HistorySection() {
  const [recordType, setRecordType] = useState('')
  const [limit, setLimit] = useState('20')
  const [records, setRecords] = useState<MemoryRecordResponse[] | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const result = await getMemoryHistory(recordType || undefined, Number(limit) || undefined)
      setRecords(result.records)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card title="Chronological History">
      <div className="flex flex-wrap gap-2">
        <select
          value={recordType}
          onChange={(e) => setRecordType(e.target.value)}
          className="rounded-md border border-vidur-border bg-vidur-surface-raised px-3 py-2 text-sm text-vidur-text focus:border-vidur-accent focus:outline-none"
        >
          <option value="">Any record type</option>
          {RECORD_TYPES.map((type) => (
            <option key={type} value={type}>{type}</option>
          ))}
        </select>
        <TextInput value={limit} onChange={setLimit} placeholder="limit" className="w-24" />
        <PrimaryButton onClick={() => void load()} disabled={loading}>
          {loading ? 'Loading…' : 'Load History'}
        </PrimaryButton>
      </div>
      <ErrorBanner error={error} />
      {records ? (
        records.length === 0 ? (
          <EmptyState message="No recorded history." />
        ) : (
          <ul className="mt-3 space-y-2">
            {records.map((record) => (
              <MemoryRecordItem key={record.record_id} record={record} />
            ))}
          </ul>
        )
      ) : null}
    </Card>
  )
}

function MemoryRecordItem({ record, similarity }: { record: MemoryRecordResponse; similarity?: number }) {
  return (
    <li className="rounded-md border border-vidur-border p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs uppercase text-vidur-text-muted">{record.record_type} · {record.recorded_at}</span>
        {similarity !== undefined ? <span className="text-xs text-vidur-accent">similarity {similarity.toFixed(2)}</span> : null}
      </div>
      <p className="text-sm text-vidur-text">{record.summary}</p>
      {record.health_score !== null && record.health_score !== undefined ? (
        <p className="text-xs text-vidur-text-muted">Health score: {record.health_score.toFixed(1)}</p>
      ) : null}
    </li>
  )
}
