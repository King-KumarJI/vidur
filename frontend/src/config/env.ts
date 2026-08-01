/**
 * Central runtime configuration. `PROJECT_ID_HEADER` mirrors
 * `DEFAULT_PROJECT_ID_HEADER` in backend/app/config/settings.py — every
 * outgoing request attaches it from services/apiClient.ts alone, never
 * per call site.
 */
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export const API_V1_PREFIX = '/api/v1'

export const PROJECT_ID_HEADER = 'X-Project-Id'

export const PROJECT_ID_STORAGE_KEY = 'vidur.activeProjectId'

export const RECENT_PROJECTS_STORAGE_KEY = 'vidur.recentProjectIds'
