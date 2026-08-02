import { useCallback, useEffect, useState } from 'react'
import { WeeklyCodingTimeChart } from '../components/WeeklyCodingTimeChart'
import { Badge, Card, EmptyState, ErrorBanner, PrimaryButton, Spinner, TextInput } from '../components/ui'
import { useProject } from '../context/ProjectContext'
import {
  addSpecsDeadline,
  getCurrentSpecsSnapshot,
  getSpecsPrediction,
  ingestSpecs,
  listSpecsDeadlines,
} from '../services/apiClient'
import type {
  DeadlineResponse,
  MetricReadingResponse,
  SpecsPredictionReportResponse,
  SpecsSnapshotResponse,
} from '../services/types'

const SNAPSHOT_POLL_INTERVAL_MS = 15_000
const DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

export function SpecsPage() {
  const { projectId } = useProject()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-vidur-text">Specs</h1>
        <p className="text-sm text-vidur-text-muted">
          Personal / Computer / Calendar / Environmental telemetry (feature flag{' '}
          <code>MAJOR_IOT_ENVIRONMENTAL_ANALYTICS</code>) and the Specs ML Prediction Engine (feature flag{' '}
          <code>MAJOR_PREDICTIVE_DASHBOARDS</code>), both Major Project capabilities disabled by default.
        </p>
      </div>

      {!projectId ? (
        <ErrorBanner error={new Error('Select an active project on the Projects page before viewing Specs.')} />
      ) : (
        <>
          <CurrentReadingsSection />
          <ManualInputSection />
          <CalendarSection />
          <PredictionSection />
        </>
      )}
    </div>
  )
}

function MetricTile({
  label,
  reading,
  showSource = false,
}: {
  label: string
  reading: MetricReadingResponse
  showSource?: boolean
}) {
  const missing = reading.status !== 'present'
  return (
    <li className="rounded-md border border-vidur-border p-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm text-vidur-text">{label}</span>
        {showSource && !missing && reading.source ? <Badge label={reading.source} /> : null}
      </div>
      {missing ? (
        <p className="text-xs text-vidur-text-muted">Not detected</p>
      ) : (
        <p className="text-lg font-semibold text-vidur-text">
          {reading.value?.toFixed(1)}{' '}
          <span className="text-xs font-normal text-vidur-text-muted">{reading.unit}</span>
        </p>
      )}
    </li>
  )
}

function CurrentReadingsSection() {
  const [snapshot, setSnapshot] = useState<SpecsSnapshotResponse | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function poll() {
      try {
        const result = await getCurrentSpecsSnapshot()
        if (!cancelled) {
          setSnapshot(result)
          setError(null)
        }
      } catch (err) {
        if (!cancelled) setError(err)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void poll()
    const interval = window.setInterval(() => void poll(), SNAPSHOT_POLL_INTERVAL_MS)
    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [])

  return (
    <Card title="Current Readings">
      <ErrorBanner error={error} />
      {loading && !snapshot ? (
        <Spinner label="Loading current readings…" />
      ) : snapshot ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div>
            <p className="mb-2 text-xs uppercase tracking-wide text-vidur-text-muted">Personal</p>
            <ul className="space-y-2">
              <MetricTile label="Last session duration" reading={snapshot.personal.last_session_duration_minutes} />
              <MetricTile label="Sleep hours" reading={snapshot.personal.sleep_hours} />
              <MetricTile label="Caffeine intake" reading={snapshot.personal.caffeine_intake_mg} />
              <MetricTile label="Typing speed" reading={snapshot.personal.typing_speed_cpm} />
              <MetricTile label="Mouse activity" reading={snapshot.personal.mouse_activity_rate} />
              <MetricTile label="Break frequency" reading={snapshot.personal.break_frequency_per_hour} />
            </ul>
          </div>
          <div>
            <p className="mb-2 text-xs uppercase tracking-wide text-vidur-text-muted">Computer</p>
            <ul className="space-y-2">
              <MetricTile label="CPU usage" reading={snapshot.computer.cpu_usage_percent} />
              <MetricTile label="RAM usage" reading={snapshot.computer.ram_usage_percent} />
              <MetricTile label="Disk I/O" reading={snapshot.computer.disk_io_kbps} />
              <MetricTile label="Internet latency" reading={snapshot.computer.internet_latency_ms} />
            </ul>
          </div>
          <div>
            <p className="mb-2 text-xs uppercase tracking-wide text-vidur-text-muted">Environmental</p>
            <ul className="space-y-2">
              <MetricTile label="Temperature" reading={snapshot.environmental.temperature_celsius} showSource />
              <MetricTile label="Humidity" reading={snapshot.environmental.humidity_percent} showSource />
              <MetricTile label="Ambient light" reading={snapshot.environmental.ambient_light_lux} showSource />
              <MetricTile label="Noise level" reading={snapshot.environmental.noise_level_db} showSource />
            </ul>
          </div>
        </div>
      ) : null}
    </Card>
  )
}

function ManualInputSection() {
  const [sleepHours, setSleepHours] = useState('')
  const [caffeineMg, setCaffeineMg] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [success, setSuccess] = useState(false)

  async function handleSubmit() {
    setSubmitting(true)
    setError(null)
    setSuccess(false)
    try {
      await ingestSpecs({
        personal: {
          sleep_hours: sleepHours.trim() ? Number(sleepHours) : undefined,
          caffeine_intake_mg: caffeineMg.trim() ? Number(caffeineMg) : undefined,
        },
      })
      setSuccess(true)
      setSleepHours('')
      setCaffeineMg('')
    } catch (err) {
      setError(err)
    } finally {
      setSubmitting(false)
    }
  }

  const canSubmit = sleepHours.trim().length > 0 || caffeineMg.trim().length > 0

  return (
    <Card title="Manual Input">
      <div className="flex flex-wrap items-center gap-3">
        <TextInput value={sleepHours} onChange={setSleepHours} placeholder="Sleep hours" className="w-40" />
        <TextInput value={caffeineMg} onChange={setCaffeineMg} placeholder="Caffeine intake (mg)" className="w-48" />
        <PrimaryButton onClick={() => void handleSubmit()} disabled={submitting || !canSubmit}>
          {submitting ? 'Submitting…' : 'Submit'}
        </PrimaryButton>
      </div>
      {success ? <p className="mt-2 text-sm text-vidur-good">Recorded.</p> : null}
      <ErrorBanner error={error} />
    </Card>
  )
}

function CalendarSection() {
  const [now, setNow] = useState(() => new Date())
  const [deadlines, setDeadlines] = useState<DeadlineResponse[] | null>(null)
  const [listError, setListError] = useState<unknown>(null)
  const [title, setTitle] = useState('')
  const [dueAt, setDueAt] = useState('')
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<unknown>(null)

  useEffect(() => {
    const interval = window.setInterval(() => setNow(new Date()), 1000)
    return () => window.clearInterval(interval)
  }, [])

  const loadDeadlines = useCallback(async () => {
    try {
      const result = await listSpecsDeadlines()
      setDeadlines(result)
      setListError(null)
    } catch (err) {
      setListError(err)
    }
  }, [])

  useEffect(() => {
    void loadDeadlines()
  }, [loadDeadlines])

  async function handleAddDeadline() {
    if (!title.trim() || !dueAt) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      await addSpecsDeadline({
        title: title.trim(),
        due_at: new Date(dueAt).toISOString(),
        notes: notes.trim() || undefined,
      })
      setTitle('')
      setDueAt('')
      setNotes('')
      await loadDeadlines()
    } catch (err) {
      setSubmitError(err)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card title="Calendar">
      <div className="mb-4 flex items-baseline gap-3">
        <p className="text-2xl font-semibold text-vidur-text">{now.toLocaleTimeString()}</p>
        <p className="text-sm text-vidur-text-muted">{DAY_NAMES[now.getDay()]}</p>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <TextInput value={title} onChange={setTitle} placeholder="Deadline title" className="min-w-48 flex-1" />
        <input
          type="datetime-local"
          value={dueAt}
          onChange={(e) => setDueAt(e.target.value)}
          className="rounded-md border border-vidur-border bg-vidur-surface-raised px-3 py-2 text-sm text-vidur-text focus:border-vidur-accent focus:outline-none"
        />
        <TextInput value={notes} onChange={setNotes} placeholder="Notes (optional)" className="min-w-40 flex-1" />
        <PrimaryButton onClick={() => void handleAddDeadline()} disabled={submitting || !title.trim() || !dueAt}>
          {submitting ? 'Adding…' : 'Add Deadline'}
        </PrimaryButton>
      </div>
      <ErrorBanner error={submitError} />

      <ErrorBanner error={listError} />
      {listError ? null : deadlines === null ? (
        <Spinner label="Loading deadlines…" />
      ) : deadlines.length === 0 ? (
        <EmptyState message="No deadlines recorded." />
      ) : (
        <ul className="space-y-1">
          {deadlines.map((deadline) => (
            <li
              key={deadline.deadline_id}
              className="flex items-center justify-between gap-2 rounded-md border border-vidur-border p-2 text-sm"
            >
              <div>
                <span className="text-vidur-text">{deadline.title}</span>
                {deadline.notes ? <span className="ml-2 text-xs text-vidur-text-muted">{deadline.notes}</span> : null}
              </div>
              <span className="text-xs text-vidur-text-muted">{new Date(deadline.due_at).toLocaleString()}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

function PredictionSection() {
  const [report, setReport] = useState<SpecsPredictionReportResponse | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setReport(await getSpecsPrediction())
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <Card title="Prediction">
      <div className="mb-3 flex justify-end">
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="text-xs text-vidur-accent hover:underline disabled:opacity-50"
        >
          Refresh
        </button>
      </div>
      <ErrorBanner error={error} />
      {loading && !report ? (
        <Spinner label="Loading prediction…" />
      ) : report ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <Card title="Upcoming Session">
              <p className="text-2xl font-semibold text-vidur-text">
                {(report.upcoming_session.likelihood_score * 100).toFixed(0)}%
              </p>
              <Badge label={report.upcoming_session.confidence} />
              {report.upcoming_session.predicted_duration_minutes != null ? (
                <p className="mt-1 text-sm text-vidur-text-muted">
                  ~{report.upcoming_session.predicted_duration_minutes.toFixed(0)} min
                  {report.upcoming_session.predicted_success_score != null
                    ? `, success score ${report.upcoming_session.predicted_success_score.toFixed(0)}`
                    : ''}
                </p>
              ) : null}
              <p className="mt-1 text-xs text-vidur-text-muted">{report.upcoming_session.basis}</p>
            </Card>

            <Card title="Last Session">
              {report.last_session.has_session ? (
                <>
                  <p className="text-2xl font-semibold text-vidur-text">
                    {report.last_session.duration_minutes?.toFixed(0)} min
                  </p>
                  {report.last_session.success_score != null ? (
                    <p className="text-sm text-vidur-text-muted">
                      Success score: {report.last_session.success_score.toFixed(0)}
                    </p>
                  ) : null}
                  <p className="mt-1 text-xs text-vidur-text-muted">{report.last_session.message}</p>
                </>
              ) : (
                <EmptyState message={report.last_session.message} />
              )}
            </Card>

            <Card title="Last 5 Sessions">
              <p className="text-2xl font-semibold text-vidur-text">
                {report.recent_sessions.average_success_score != null
                  ? report.recent_sessions.average_success_score.toFixed(0)
                  : '—'}
              </p>
              <p className="text-xs text-vidur-text-muted">
                {report.recent_sessions.sessions_considered} session(s) considered
              </p>
              <p className="mt-1 text-xs text-vidur-text-muted">{report.recent_sessions.message}</p>
            </Card>
          </div>

          <Card title="Weekly Coding Time">
            <WeeklyCodingTimeChart points={report.weekly_coding_time.points} />
          </Card>
        </div>
      ) : null}
    </Card>
  )
}
