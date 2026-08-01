import { useState } from 'react'
import { useProject } from '../context/ProjectContext'
import { PrimaryButton, TextInput } from './ui'

/** Always-visible header control for switching the active Project ID.
 * Mirrors the fuller ProjectsPage but scoped to quick switching. */
export function ProjectSwitcher() {
  const { projectId, recentProjectIds, isValidating, validationError, switchProject, clearProject } = useProject()
  const [draft, setDraft] = useState('')
  const [open, setOpen] = useState(false)

  async function handleSwitch(candidate: string) {
    const ok = await switchProject(candidate)
    if (ok) {
      setDraft('')
      setOpen(false)
    }
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-md border border-vidur-border bg-vidur-surface-raised px-3 py-1.5 text-sm hover:border-vidur-accent"
      >
        <span className="h-2 w-2 rounded-full" style={{ background: projectId ? 'var(--color-vidur-good)' : 'var(--color-vidur-text-muted)' }} />
        {projectId ?? 'No project selected'}
      </button>

      {open ? (
        <div className="absolute right-0 z-20 mt-2 w-80 rounded-md border border-vidur-border bg-vidur-surface p-3 shadow-xl">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              if (draft.trim()) void handleSwitch(draft.trim())
            }}
            className="flex gap-2"
          >
            <TextInput value={draft} onChange={setDraft} placeholder="project-id" className="flex-1" />
            <PrimaryButton type="submit" disabled={isValidating || !draft.trim()}>
              Set
            </PrimaryButton>
          </form>
          {validationError ? <p className="mt-2 text-xs text-vidur-bad">{validationError}</p> : null}

          {recentProjectIds.length > 0 ? (
            <div className="mt-3">
              <p className="mb-1 text-xs uppercase tracking-wide text-vidur-text-muted">Recent</p>
              <ul className="max-h-40 space-y-1 overflow-y-auto">
                {recentProjectIds.map((id) => (
                  <li key={id}>
                    <button
                      type="button"
                      onClick={() => void handleSwitch(id)}
                      className={`w-full truncate rounded px-2 py-1 text-left text-sm hover:bg-vidur-surface-raised ${id === projectId ? 'text-vidur-accent' : 'text-vidur-text'}`}
                    >
                      {id}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {projectId ? (
            <button type="button" onClick={clearProject} className="mt-3 text-xs text-vidur-text-muted hover:text-vidur-bad">
              Clear active project
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
