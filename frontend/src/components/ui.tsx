import type { ReactNode } from 'react'
import { ApiError } from '../services/apiClient'

export function Card({ title, children, className = '' }: { title?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-lg border border-vidur-border bg-vidur-surface p-5 ${className}`}>
      {title ? <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-vidur-text-muted">{title}</h3> : null}
      {children}
    </div>
  )
}

const LEVEL_COLORS: Record<string, string> = {
  low: 'bg-vidur-good/15 text-vidur-good',
  info: 'bg-vidur-info/15 text-vidur-info',
  medium: 'bg-vidur-warn/15 text-vidur-warn',
  warning: 'bg-vidur-warn/15 text-vidur-warn',
  high: 'bg-vidur-serious/15 text-vidur-serious',
  serious: 'bg-vidur-serious/15 text-vidur-serious',
  critical: 'bg-vidur-bad/15 text-vidur-bad',
  error: 'bg-vidur-bad/15 text-vidur-bad',
}

export function Badge({ label }: { label: string }) {
  const color = LEVEL_COLORS[label.toLowerCase()] ?? 'bg-vidur-accent-muted text-vidur-text'
  return <span className={`rounded px-2 py-0.5 text-xs font-medium ${color}`}>{label}</span>
}

export function Spinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-vidur-text-muted">
      <span className="h-3 w-3 animate-spin rounded-full border-2 border-vidur-accent border-t-transparent" />
      {label}
    </div>
  )
}

export function ErrorBanner({ error }: { error: unknown }) {
  if (!error) return null
  if (error instanceof ApiError && error.isFeatureDisabled) {
    return (
      <div className="rounded-md border border-vidur-warn/40 bg-vidur-warn/10 px-4 py-3 text-sm text-vidur-warn">
        This capability is a Major Project feature and is currently disabled via its feature flag
        ({error.errorCode}). Enable it in <code className="text-vidur-warn">backend/app/config/feature_flags.py</code> to use this page.
      </div>
    )
  }
  const message = error instanceof Error ? error.message : String(error)
  return (
    <div className="rounded-md border border-vidur-bad/40 bg-vidur-bad/10 px-4 py-3 text-sm text-vidur-bad">
      {message}
    </div>
  )
}

export function EmptyState({ message }: { message: string }) {
  return <p className="text-sm text-vidur-text-muted">{message}</p>
}

export function PrimaryButton({
  children,
  disabled,
  onClick,
  type = 'button',
}: {
  children: ReactNode
  disabled?: boolean
  onClick?: () => void
  type?: 'button' | 'submit'
}) {
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className="rounded-md bg-vidur-accent px-4 py-2 text-sm font-medium text-white transition hover:bg-vidur-accent/80 disabled:cursor-not-allowed disabled:opacity-50"
    >
      {children}
    </button>
  )
}

export function TextInput({
  value,
  onChange,
  placeholder,
  className = '',
}: {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
}) {
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className={`rounded-md border border-vidur-border bg-vidur-surface-raised px-3 py-2 text-sm text-vidur-text placeholder:text-vidur-text-muted focus:border-vidur-accent focus:outline-none ${className}`}
    />
  )
}
