import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { ApiError, validateProjectId } from '../services/apiClient'
import {
  getActiveProjectId,
  getRecentProjectIds,
  initProjectIdFromStorage,
  setActiveProjectId,
  subscribeToProjectId,
} from '../services/projectId'

interface ProjectContextValue {
  projectId: string | null
  recentProjectIds: string[]
  isValidating: boolean
  validationError: string | null
  /** Validates a candidate Project ID against POST /projects/validate
   * and, if valid, makes it the active project. Returns whether it
   * became active. */
  switchProject: (candidateProjectId: string) => Promise<boolean>
  clearProject: () => void
}

const ProjectContext = createContext<ProjectContextValue | null>(null)

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [projectId, setProjectId] = useState<string | null>(null)
  const [recentProjectIds, setRecentProjectIds] = useState<string[]>([])
  const [isValidating, setIsValidating] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)

  useEffect(() => {
    setProjectId(initProjectIdFromStorage())
    setRecentProjectIds(getRecentProjectIds())
    return subscribeToProjectId((next) => {
      setProjectId(next)
      setRecentProjectIds(getRecentProjectIds())
    })
  }, [])

  const switchProject = useCallback(async (candidateProjectId: string): Promise<boolean> => {
    setIsValidating(true)
    setValidationError(null)
    try {
      const result = await validateProjectId(candidateProjectId)
      if (!result.valid) {
        setValidationError(`"${candidateProjectId}" is not a valid Project ID.`)
        return false
      }
      setActiveProjectId(result.project_id)
      return true
    } catch (err) {
      setValidationError(err instanceof ApiError ? err.message : 'Failed to validate Project ID.')
      return false
    } finally {
      setIsValidating(false)
    }
  }, [])

  const clearProject = useCallback(() => {
    setActiveProjectId(null)
  }, [])

  const value = useMemo<ProjectContextValue>(
    () => ({
      projectId,
      recentProjectIds,
      isValidating,
      validationError,
      switchProject,
      clearProject,
    }),
    [projectId, recentProjectIds, isValidating, validationError, switchProject, clearProject],
  )

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>
}

export function useProject(): ProjectContextValue {
  const ctx = useContext(ProjectContext)
  if (!ctx) throw new Error('useProject must be used within a ProjectProvider')
  return ctx
}

export function useProjectId(): string | null {
  return useProject().projectId
}

// Re-exported so components that only need a live snapshot without
// subscribing to context re-renders can call it directly.
export { getActiveProjectId }
