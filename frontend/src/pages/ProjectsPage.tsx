import { useEffect, useState, type FormEvent } from 'react'
import { Card, ErrorBanner, PrimaryButton, Spinner, TextInput } from '../components/ui'
import { useProject } from '../context/ProjectContext'
import { getProjectResources } from '../services/apiClient'
import type { ProjectResourcesResponse } from '../services/types'

export function ProjectsPage() {
  const { projectId, recentProjectIds, isValidating, validationError, switchProject, clearProject } = useProject()
  const [draft, setDraft] = useState('')

  const [resources, setResources] = useState<ProjectResourcesResponse | null>(null)
  const [resourcesError, setResourcesError] = useState<unknown>(null)
  const [resourcesLoading, setResourcesLoading] = useState(false)

  useEffect(() => {
    if (!projectId) {
      setResources(null)
      return
    }
    let cancelled = false
    setResourcesLoading(true)
    setResourcesError(null)
    getProjectResources(projectId)
      .then((result) => !cancelled && setResources(result))
      .catch((err) => !cancelled && setResourcesError(err))
      .finally(() => !cancelled && setResourcesLoading(false))
    return () => {
      cancelled = true
    }
  }, [projectId])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!draft.trim()) return
    const ok = await switchProject(draft.trim())
    if (ok) setDraft('')
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-vidur-text">Projects</h1>
        <p className="text-sm text-vidur-text-muted">
          VIDUR enforces per-project isolation (Article 21) — every project-scoped page requires an active
          Project ID, validated and attached as the <code>X-Project-Id</code> header on every request.
        </p>
      </div>

      <Card title="Active Project">
        {projectId ? (
          <div className="flex items-center justify-between">
            <p className="text-lg text-vidur-text">{projectId}</p>
            <button type="button" onClick={clearProject} className="text-sm text-vidur-text-muted hover:text-vidur-bad">
              Clear
            </button>
          </div>
        ) : (
          <p className="text-sm text-vidur-text-muted">No project selected.</p>
        )}
      </Card>

      <Card title="Set / Validate a Project ID">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <TextInput value={draft} onChange={setDraft} placeholder="e.g. my-project" className="flex-1" />
          <PrimaryButton type="submit" disabled={isValidating || !draft.trim()}>
            {isValidating ? 'Validating…' : 'Validate & Activate'}
          </PrimaryButton>
        </form>
        {validationError ? <p className="mt-2 text-sm text-vidur-bad">{validationError}</p> : null}
      </Card>

      {recentProjectIds.length > 0 ? (
        <Card title="Recent Projects">
          <ul className="space-y-1">
            {recentProjectIds.map((id) => (
              <li key={id} className="flex items-center justify-between rounded px-2 py-1.5 hover:bg-vidur-surface-raised">
                <span className={id === projectId ? 'text-vidur-accent' : 'text-vidur-text'}>{id}</span>
                {id !== projectId ? (
                  <button type="button" onClick={() => void switchProject(id)} className="text-xs text-vidur-text-muted hover:text-vidur-accent">
                    Switch
                  </button>
                ) : (
                  <span className="text-xs text-vidur-good">Active</span>
                )}
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      <Card title="Isolated Resource Names">
        {!projectId ? (
          <p className="text-sm text-vidur-text-muted">Select a project to derive its isolated MongoDB/ChromaDB resource names.</p>
        ) : resourcesLoading ? (
          <Spinner label="Deriving resource names…" />
        ) : resourcesError ? (
          <ErrorBanner error={resourcesError} />
        ) : resources ? (
          <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-vidur-text-muted">MongoDB database</dt>
              <dd className="font-mono text-vidur-text">{resources.mongodb_database}</dd>
            </div>
            <div>
              <dt className="text-vidur-text-muted">ChromaDB collection</dt>
              <dd className="font-mono text-vidur-text">{resources.chromadb_collection}</dd>
            </div>
          </dl>
        ) : null}
      </Card>
    </div>
  )
}
