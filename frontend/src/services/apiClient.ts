import { API_BASE_URL, API_V1_PREFIX, PROJECT_ID_HEADER } from '../config/env'
import { getActiveProjectId } from './projectId'
import type {
  AppInfoResponse,
  DatabaseHealthResponse,
  FeatureFlagsResponse,
  HealthScoreTrendResponse,
  InspectionReportResponse,
  MLPredictionReportResponse,
  MemoryHistoryResponse,
  MemoryRecallMatchResponse,
  NLPReportResponse,
  ProjectResourcesResponse,
  ProjectValidationResponse,
  ReasoningReportResponse,
  VisualComparisonReportResponse,
  VisualComparisonRunRequest,
} from './types'

/** Uniform error thrown for every non-2xx response. `status` lets
 * callers special-case HTTP 403 (a Major-tier feature flag disabled)
 * without string-matching `message`. */
export class ApiError extends Error {
  readonly status: number
  readonly errorCode: string

  constructor(status: number, errorCode: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.errorCode = errorCode
  }

  get isFeatureDisabled(): boolean {
    return this.status === 403
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST'
  body?: unknown
  query?: Record<string, string | number | string[] | undefined>
  /** Project-scoped routes require an active Project ID; exempt
   * routes (config, projects, health) must not send the header at
   * all so they keep working before any project is selected. */
  projectScoped?: boolean
}

function buildQueryString(query: RequestOptions['query']): string {
  if (!query) return ''
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined) continue
    if (Array.isArray(value)) {
      for (const item of value) params.append(key, item)
    } else {
      params.append(key, String(value))
    }
  }
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, query, projectScoped = false } = options

  const headers: Record<string, string> = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  if (projectScoped) {
    const projectId = getActiveProjectId()
    if (!projectId) {
      throw new ApiError(400, 'missing_project_id', 'No active project selected.')
    }
    headers[PROJECT_ID_HEADER] = projectId
  }

  const response = await fetch(`${API_BASE_URL}${path}${buildQueryString(query)}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (!response.ok) {
    let errorCode = 'http_error'
    let message = response.statusText || `Request failed with status ${response.status}`
    try {
      const data = await response.json()
      if (typeof data.error === 'string') errorCode = data.error
      if (typeof data.message === 'string') message = data.message
      else if (Array.isArray(data.detail)) {
        errorCode = 'validation_error'
        message = data.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join('; ') || message
      }
    } catch {
      // Response body was not JSON; fall back to statusText above.
    }
    throw new ApiError(response.status, errorCode, message)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

// ---- DB Health (top-level /health, exempt from project scoping) ----

export function getDatabaseHealth(): Promise<DatabaseHealthResponse> {
  return request<DatabaseHealthResponse>('/health')
}

// ---- Config (exempt from project scoping) ----

export function getAppInfo(): Promise<AppInfoResponse> {
  return request<AppInfoResponse>(`${API_V1_PREFIX}/config/info`)
}

export function getFeatureFlags(): Promise<FeatureFlagsResponse> {
  return request<FeatureFlagsResponse>(`${API_V1_PREFIX}/config/feature-flags`)
}

// ---- Project Isolation (exempt from project scoping) ----

export function validateProjectId(projectId: string): Promise<ProjectValidationResponse> {
  return request<ProjectValidationResponse>(`${API_V1_PREFIX}/projects/validate`, {
    method: 'POST',
    body: { project_id: projectId },
  })
}

export function getProjectResources(projectId: string): Promise<ProjectResourcesResponse> {
  return request<ProjectResourcesResponse>(
    `${API_V1_PREFIX}/projects/${encodeURIComponent(projectId)}/resources`,
  )
}

// ---- Inspection Engine (project-scoped) ----

export function runInspection(rootPath: string): Promise<InspectionReportResponse> {
  return request<InspectionReportResponse>(`${API_V1_PREFIX}/inspection/run`, {
    method: 'POST',
    body: { root_path: rootPath },
    projectScoped: true,
  })
}

// ---- AI Reasoning (project-scoped) ----

export function runAIReasoning(rootPath: string): Promise<ReasoningReportResponse> {
  return request<ReasoningReportResponse>(`${API_V1_PREFIX}/ai-reasoning/run`, {
    method: 'POST',
    body: { root_path: rootPath },
    projectScoped: true,
  })
}

// ---- NLP (project-scoped) ----

export function runNLPAnalysis(rootPath: string): Promise<NLPReportResponse> {
  return request<NLPReportResponse>(`${API_V1_PREFIX}/nlp/run`, {
    method: 'POST',
    body: { root_path: rootPath },
    projectScoped: true,
  })
}

// ---- ML Prediction (project-scoped, Major-tier flag: MAJOR_ML_RISK_PREDICTION) ----

export function runMLPrediction(
  rootPath: string,
  includeReasoning: boolean,
): Promise<MLPredictionReportResponse> {
  return request<MLPredictionReportResponse>(`${API_V1_PREFIX}/ml-prediction/run`, {
    method: 'POST',
    body: { root_path: rootPath, include_reasoning: includeReasoning },
    projectScoped: true,
  })
}

// ---- Deep Learning Vision (project-scoped, Major-tier flag: MAJOR_DEEP_LEARNING_VISUAL_INSPECTION) ----

export function runVisualComparison(
  body: VisualComparisonRunRequest,
): Promise<VisualComparisonReportResponse> {
  return request<VisualComparisonReportResponse>(`${API_V1_PREFIX}/deep-learning-vision/compare`, {
    method: 'POST',
    body,
    projectScoped: true,
  })
}

// ---- Memory (project-scoped) ----

export function recallMemory(
  queryText: string,
  topK: number,
  recordType?: string,
): Promise<MemoryRecallMatchResponse[]> {
  return request<MemoryRecallMatchResponse[]>(`${API_V1_PREFIX}/memory/recall`, {
    method: 'POST',
    body: { query_text: queryText, top_k: topK, record_type: recordType ?? null },
    projectScoped: true,
  })
}

export function getMemoryHistory(
  recordType?: string,
  limit?: number,
): Promise<MemoryHistoryResponse> {
  return request<MemoryHistoryResponse>(`${API_V1_PREFIX}/memory/history`, {
    query: { record_type: recordType, limit },
    projectScoped: true,
  })
}

export function getHealthScoreTrend(
  recordTypes?: string[],
  limit?: number,
): Promise<HealthScoreTrendResponse> {
  return request<HealthScoreTrendResponse>(`${API_V1_PREFIX}/memory/health-score-trend`, {
    query: { record_types: recordTypes, limit },
    projectScoped: true,
  })
}
