import { useState, type FormEvent, type ReactNode } from 'react'
import { PrimaryButton, TextInput } from './ui'

/** Shared "root_path + Run" form used by every pipeline page (Inspection,
 * AI Reasoning, NLP, ML Prediction) that runs analysis against a project
 * root already present on the VIDUR backend's own file system. */
export function RootPathForm({
  onRun,
  running,
  runLabel = 'Run',
  extraControls,
}: {
  onRun: (rootPath: string) => void
  running: boolean
  runLabel?: string
  extraControls?: ReactNode
}) {
  const [rootPath, setRootPath] = useState('')

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (rootPath.trim()) onRun(rootPath.trim())
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-center gap-3">
      <TextInput
        value={rootPath}
        onChange={setRootPath}
        placeholder="Absolute path to project root, e.g. C:\path\to\project"
        className="min-w-80 flex-1"
      />
      {extraControls}
      <PrimaryButton type="submit" disabled={running || !rootPath.trim()}>
        {running ? 'Running…' : runLabel}
      </PrimaryButton>
    </form>
  )
}
