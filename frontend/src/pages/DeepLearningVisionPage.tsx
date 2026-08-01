import { useState } from 'react'
import { Badge, Card, EmptyState, ErrorBanner, PrimaryButton, Spinner, TextInput } from '../components/ui'
import { useProject } from '../context/ProjectContext'
import { runVisualComparison } from '../services/apiClient'
import type {
  LayoutElementInput,
  PixelImageInput,
  VisualComparisonReportResponse,
  VisualSnapshotInput,
} from '../services/types'

interface LayoutElementRow extends LayoutElementInput {
  rowId: string
}

interface SnapshotDraft {
  label: string
  elements: LayoutElementRow[]
  imageJson: string
}

function emptySnapshot(label: string): SnapshotDraft {
  return { label, elements: [], imageJson: '' }
}

function newRow(): LayoutElementRow {
  return {
    rowId: crypto.randomUUID(),
    element_id: '',
    tag: '',
    bounds: { x: 0, y: 0, width: 0, height: 0 },
    text: '',
  }
}

function buildSnapshotInput(draft: SnapshotDraft): VisualSnapshotInput {
  let image: PixelImageInput | undefined
  if (draft.imageJson.trim()) {
    image = JSON.parse(draft.imageJson) as PixelImageInput
  }
  return {
    label: draft.label,
    image,
    layout: draft.elements.length > 0
      ? { elements: draft.elements.map(({ rowId: _rowId, ...el }) => el) }
      : undefined,
  }
}

export function DeepLearningVisionPage() {
  const { projectId } = useProject()
  const [baseline, setBaseline] = useState<SnapshotDraft>(emptySnapshot('baseline'))
  const [current, setCurrent] = useState<SnapshotDraft>(emptySnapshot('current'))
  const [canvasWidth, setCanvasWidth] = useState('')
  const [canvasHeight, setCanvasHeight] = useState('')
  const [report, setReport] = useState<VisualComparisonReportResponse | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [running, setRunning] = useState(false)

  async function handleSubmit() {
    setRunning(true)
    setError(null)
    setReport(null)
    try {
      const body = {
        baseline: buildSnapshotInput(baseline),
        current: buildSnapshotInput(current),
        canvas_width: canvasWidth ? Number(canvasWidth) : undefined,
        canvas_height: canvasHeight ? Number(canvasHeight) : undefined,
      }
      setReport(await runVisualComparison(body))
    } catch (err) {
      setError(err instanceof SyntaxError ? new Error(`Invalid image JSON: ${err.message}`) : err)
    } finally {
      setRunning(false)
    }
  }

  const canSubmit = baseline.label.trim().length > 0 && current.label.trim().length > 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-vidur-text">Deep Learning Vision</h1>
        <p className="text-sm text-vidur-text-muted">
          Major Project capability (feature flag <code>MAJOR_DEEP_LEARNING_VISUAL_INSPECTION</code>,
          disabled by default). Compares two caller-supplied visual snapshots for pixel and layout
          regressions. Provide layout elements manually, or paste a raw pixel-image JSON blob.
        </p>
      </div>

      {!projectId ? (
        <ErrorBanner error={new Error('Select an active project on the Projects page before running a visual comparison.')} />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <SnapshotEditor title="Baseline Snapshot" draft={baseline} onChange={setBaseline} />
            <SnapshotEditor title="Current Snapshot" draft={current} onChange={setCurrent} />
          </div>

          <Card title="Canvas Dimensions (optional)">
            <div className="flex gap-3">
              <TextInput value={canvasWidth} onChange={setCanvasWidth} placeholder="Canvas width (px)" className="w-48" />
              <TextInput value={canvasHeight} onChange={setCanvasHeight} placeholder="Canvas height (px)" className="w-48" />
            </div>
          </Card>

          <PrimaryButton onClick={() => void handleSubmit()} disabled={running || !canSubmit}>
            {running ? 'Comparing…' : 'Compare Snapshots'}
          </PrimaryButton>
        </>
      )}

      {running ? <Spinner label="Comparing snapshots…" /> : null}
      <ErrorBanner error={error} />

      {report ? (
        <div className="space-y-4">
          <Card title="Verdict">
            <div className="flex items-center gap-2">
              <Badge label={report.verdict} />
              <p className="text-sm text-vidur-text">{report.summary}</p>
            </div>
          </Card>

          {report.pixel_diff ? (
            <Card title="Pixel Diff">
              <p className="text-sm text-vidur-text-muted">
                {report.pixel_diff.changed_pixel_count} / {report.pixel_diff.total_pixel_count} pixels changed
                ({(report.pixel_diff.diff_ratio * 100).toFixed(1)}%) · <Badge label={report.pixel_diff.risk_level} />
              </p>
              {report.pixel_diff.regions.length > 0 ? (
                <p className="mt-1 text-xs text-vidur-text-muted">{report.pixel_diff.regions.length} diff region(s)</p>
              ) : null}
            </Card>
          ) : null}

          {report.layout_diff ? (
            <Card title={`Layout Diff (${report.layout_diff.changes.length} change(s))`}>
              <div className="mb-2"><Badge label={report.layout_diff.risk_level} /></div>
              {report.layout_diff.changes.length === 0 ? (
                <EmptyState message="No layout changes." />
              ) : (
                <ul className="space-y-1 text-sm">
                  {report.layout_diff.changes.map((c, i) => (
                    <li key={i} className="text-vidur-text-muted">
                      <span className="font-mono text-vidur-text">{c.element_id}</span> — {c.change_type}: {c.detail}
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          ) : null}

          <Card title={`Consistency Issues (${report.consistency_issues.length})`}>
            {report.consistency_issues.length === 0 ? (
              <EmptyState message="No layout consistency issues." />
            ) : (
              <ul className="space-y-1 text-sm">
                {report.consistency_issues.map((issue, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <Badge label={issue.risk_level} />
                    <span className="text-vidur-text-muted">{issue.detail} ({issue.element_ids.join(', ')})</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card title={`Findings (${report.findings.length})`}>
            {report.findings.length === 0 ? (
              <EmptyState message="No visual regression findings." />
            ) : (
              <ul className="space-y-1 text-sm">
                {report.findings.map((f, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <Badge label={f.risk_level} />
                    <span className="text-vidur-text-muted">[{f.category}] {f.message}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      ) : null}
    </div>
  )
}

function SnapshotEditor({
  title,
  draft,
  onChange,
}: {
  title: string
  draft: SnapshotDraft
  onChange: (draft: SnapshotDraft) => void
}) {
  function updateElement(rowId: string, patch: Partial<LayoutElementRow>) {
    onChange({
      ...draft,
      elements: draft.elements.map((el) => (el.rowId === rowId ? { ...el, ...patch } : el)),
    })
  }

  function updateBounds(rowId: string, patch: Partial<LayoutElementRow['bounds']>) {
    onChange({
      ...draft,
      elements: draft.elements.map((el) => (el.rowId === rowId ? { ...el, bounds: { ...el.bounds, ...patch } } : el)),
    })
  }

  return (
    <Card title={title}>
      <TextInput value={draft.label} onChange={(label) => onChange({ ...draft, label })} placeholder="Snapshot label" className="w-full" />

      <div className="mt-3">
        <div className="mb-1 flex items-center justify-between">
          <p className="text-xs uppercase text-vidur-text-muted">Layout Elements</p>
          <button
            type="button"
            onClick={() => onChange({ ...draft, elements: [...draft.elements, newRow()] })}
            className="text-xs text-vidur-accent hover:underline"
          >
            + Add element
          </button>
        </div>
        {draft.elements.length === 0 ? (
          <EmptyState message="No layout elements added." />
        ) : (
          <div className="space-y-2">
            {draft.elements.map((el) => (
              <div key={el.rowId} className="grid grid-cols-6 gap-1 rounded border border-vidur-border p-2">
                <TextInput value={el.element_id} onChange={(v) => updateElement(el.rowId, { element_id: v })} placeholder="id" className="col-span-2" />
                <TextInput value={el.tag} onChange={(v) => updateElement(el.rowId, { tag: v })} placeholder="tag" className="col-span-1" />
                <TextInput value={String(el.bounds.x)} onChange={(v) => updateBounds(el.rowId, { x: Number(v) || 0 })} placeholder="x" className="col-span-1" />
                <TextInput value={String(el.bounds.y)} onChange={(v) => updateBounds(el.rowId, { y: Number(v) || 0 })} placeholder="y" className="col-span-1" />
                <button
                  type="button"
                  onClick={() => onChange({ ...draft, elements: draft.elements.filter((e) => e.rowId !== el.rowId) })}
                  className="col-span-1 text-xs text-vidur-bad hover:underline"
                >
                  remove
                </button>
                <TextInput value={String(el.bounds.width)} onChange={(v) => updateBounds(el.rowId, { width: Number(v) || 0 })} placeholder="width" className="col-span-1" />
                <TextInput value={String(el.bounds.height)} onChange={(v) => updateBounds(el.rowId, { height: Number(v) || 0 })} placeholder="height" className="col-span-1" />
                <TextInput value={el.text ?? ''} onChange={(v) => updateElement(el.rowId, { text: v })} placeholder="text (optional)" className="col-span-4" />
              </div>
            ))}
          </div>
        )}
      </div>

      <details className="mt-3">
        <summary className="cursor-pointer text-xs uppercase text-vidur-text-muted">Advanced: pixel image JSON</summary>
        <textarea
          value={draft.imageJson}
          onChange={(e) => onChange({ ...draft, imageJson: e.target.value })}
          placeholder='{"width": 100, "height": 100, "channels": 3, "pixels": [...]}'
          rows={3}
          className="mt-2 w-full rounded-md border border-vidur-border bg-vidur-surface-raised px-3 py-2 font-mono text-xs text-vidur-text placeholder:text-vidur-text-muted focus:border-vidur-accent focus:outline-none"
        />
      </details>
    </Card>
  )
}
