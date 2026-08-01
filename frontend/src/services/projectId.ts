import { PROJECT_ID_STORAGE_KEY, RECENT_PROJECTS_STORAGE_KEY } from '../config/env'

/**
 * The single source of truth for the active Project ID, read by
 * apiClient.ts to populate the X-Project-Id header on every
 * project-scoped request. React state (ProjectContext) wraps this
 * module rather than duplicating it, so the header is always in sync
 * with whatever the user last selected.
 */

let activeProjectId: string | null = null
const listeners = new Set<(projectId: string | null) => void>()

function readRecent(): string[] {
  try {
    const raw = window.localStorage.getItem(RECENT_PROJECTS_STORAGE_KEY)
    return raw ? (JSON.parse(raw) as string[]) : []
  } catch {
    return []
  }
}

function writeRecent(ids: string[]): void {
  window.localStorage.setItem(RECENT_PROJECTS_STORAGE_KEY, JSON.stringify(ids))
}

export function initProjectIdFromStorage(): string | null {
  activeProjectId = window.localStorage.getItem(PROJECT_ID_STORAGE_KEY)
  return activeProjectId
}

export function getActiveProjectId(): string | null {
  return activeProjectId
}

export function setActiveProjectId(projectId: string | null): void {
  activeProjectId = projectId
  if (projectId) {
    window.localStorage.setItem(PROJECT_ID_STORAGE_KEY, projectId)
    const recent = readRecent().filter((id) => id !== projectId)
    recent.unshift(projectId)
    writeRecent(recent.slice(0, 10))
  } else {
    window.localStorage.removeItem(PROJECT_ID_STORAGE_KEY)
  }
  for (const listener of listeners) listener(activeProjectId)
}

export function getRecentProjectIds(): string[] {
  return readRecent()
}

export function subscribeToProjectId(listener: (projectId: string | null) => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
