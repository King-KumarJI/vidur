/**
 * TypeScript mirrors of backend/app/schemas/*.py. Field-for-field with
 * the Pydantic response models — kept in sync manually, per the same
 * "single source of truth, no reinterpretation" rule the backend
 * schemas themselves follow against their engine dataclasses.
 */

// ---- common.py ----

export interface ErrorResponse {
  error: string
  message: string
}

// ---- config_schemas.py ----

export interface AppInfoResponse {
  app_name: string
  app_full_name: string
  app_version: string
  constitution_version: string
  environment: string
  debug: boolean
}

export interface FeatureFlagsResponse {
  flags: Record<string, boolean>
}

// ---- project_schemas.py ----

export interface ProjectIdRequest {
  project_id: string
}

export interface ProjectValidationResponse {
  project_id: string
  valid: boolean
}

export interface ProjectResourcesResponse {
  project_id: string
  mongodb_database: string
  chromadb_collection: string
}

// ---- health_schemas.py ----

export interface DatabaseHealthResponse {
  mongodb_connected: boolean
  chromadb_connected: boolean
  healthy: boolean
  checked_at: string
}

// ---- inspection_schemas.py ----

export interface InspectionRunRequest {
  root_path: string
}

export interface FileRecordResponse {
  relative_path: string
  absolute_path: string
  size_bytes: number
  line_count: number
  extension: string
  content_hash: string
}

export interface FileMetricsResponse {
  relative_path: string
  function_count: number
  class_count: number
  max_cyclomatic_complexity: number
  average_cyclomatic_complexity: number
  docstring_coverage: number
  has_syntax_error: boolean
}

export interface FindingResponse {
  category: string
  severity: string
  code: string
  message: string
  file_path?: string | null
  line?: number | null
}

export interface InspectionSnapshotResponse {
  project_id: string
  root_path: string
  generated_at: string
  files: Record<string, FileRecordResponse>
}

export interface InspectionReportResponse {
  project_id: string
  root_path: string
  status: string
  started_at: string
  completed_at?: string | null
  files: FileRecordResponse[]
  file_metrics: FileMetricsResponse[]
  findings: FindingResponse[]
  health_score: number
  snapshot?: InspectionSnapshotResponse | null
}

// ---- ai_reasoning_schemas.py ----

export interface ReasoningRunRequest {
  root_path: string
}

export interface IssueCorrelationGroupResponse {
  basis: string
  key: string
  findings: FindingResponse[]
  summary: string
}

export interface DependencyImpactAssessmentResponse {
  file_path: string
  direct_dependents: number
  transitive_dependents: number
  dependent_paths: string[]
  finding_count: number
  risk_score: number
}

export interface DebuggingHypothesisResponse {
  finding_code: string
  probable_cause: string
  explanation: string
  suggested_next_steps: string[]
  occurrence_count: number
  related_files: string[]
}

export interface DriftInsightResponse {
  churn_level: string
  added_count: number
  removed_count: number
  modified_count: number
  high_impact_files: string[]
  summary: string
}

export interface RecommendationResponse {
  priority: string
  category: string
  title: string
  description: string
  supporting_finding_codes: string[]
  affected_files: string[]
}

export interface ReasoningReportResponse {
  project_id: string
  root_path: string
  generated_at: string
  correlation_groups: IssueCorrelationGroupResponse[]
  dependency_assessments: DependencyImpactAssessmentResponse[]
  debugging_hypotheses: DebuggingHypothesisResponse[]
  drift_insight?: DriftInsightResponse | null
  recommendations: RecommendationResponse[]
}

// ---- nlp_schemas.py ----

export interface NLPRunRequest {
  root_path: string
}

export interface RequirementStatementResponse {
  text: string
  source_path: string
  line: number
  keywords: string[]
}

export interface DocumentedIntentResponse {
  project_title?: string | null
  declared_features: string[]
  declared_dependencies: string[]
  requirement_statements: RequirementStatementResponse[]
}

export interface ImplementedIntentResponse {
  analyzed_file_count: number
  imported_third_party_packages: string[]
  file_text_blobs: Record<string, string>
}

export interface ConsistencyFindingResponse {
  category: string
  severity: string
  code: string
  message: string
  file_path?: string | null
  line?: number | null
}

export interface SemanticSimilarityResultResponse {
  claim_text: string
  best_match_file?: string | null
  similarity_score: number
}

export interface NLPReportResponse {
  project_id: string
  root_path: string
  generated_at: string
  documented_intent: DocumentedIntentResponse
  implemented_intent: ImplementedIntentResponse
  consistency_findings: ConsistencyFindingResponse[]
  semantic_similarity_results: SemanticSimilarityResultResponse[]
}

// ---- ml_prediction_schemas.py ----

export interface MLPredictionRunRequest {
  root_path: string
  include_reasoning?: boolean
}

export interface ProjectFeatureVectorResponse {
  file_count: number
  average_cyclomatic_complexity: number
  max_cyclomatic_complexity: number
  average_docstring_coverage: number
  finding_density: number
  severity_weighted_density: number
  drift_churn_ratio: number
  average_dependency_risk: number
  max_dependency_risk: number
  health_score: number
}

export interface ModuleRiskScoreResponse {
  file_path: string
  complexity_score: number
  dependency_risk_score: number
  finding_severity_score: number
  composite_risk_score: number
  risk_level: string
}

export interface RegressionRiskPredictionResponse {
  probability: number
  risk_level: string
  contributing_factors: string[]
  summary: string
}

export interface TechnicalDebtEstimateResponse {
  debt_score: number
  risk_level: string
  estimated_remediation_hours: number
  contributing_factors: string[]
  summary: string
}

export interface QualityTrendPredictionResponse {
  direction: string
  current_health_score: number
  projected_next_health_score: number
  slope_per_run: number
  data_points_used: number
  summary: string
}

export interface FailureProbabilityPredictionResponse {
  probability: number
  risk_level: string
  contributing_factors: string[]
  summary: string
}

export interface MLPredictionReportResponse {
  project_id: string
  root_path: string
  generated_at: string
  feature_vector: ProjectFeatureVectorResponse
  module_risk_scores: ModuleRiskScoreResponse[]
  regression_risk: RegressionRiskPredictionResponse
  technical_debt: TechnicalDebtEstimateResponse
  quality_trend: QualityTrendPredictionResponse
  failure_probability: FailureProbabilityPredictionResponse
}

// ---- deep_learning_vision_schemas.py ----

export interface BoundingBoxInput {
  x: number
  y: number
  width: number
  height: number
}

export interface PixelImageInput {
  width: number
  height: number
  channels: number
  pixels: number[]
}

export interface LayoutElementInput {
  element_id: string
  tag: string
  bounds: BoundingBoxInput
  text?: string | null
}

export interface LayoutSnapshotInput {
  elements: LayoutElementInput[]
}

export interface VisualSnapshotInput {
  label: string
  captured_at?: string | null
  image?: PixelImageInput | null
  layout?: LayoutSnapshotInput | null
}

export interface VisualComparisonRunRequest {
  baseline: VisualSnapshotInput
  current: VisualSnapshotInput
  canvas_width?: number | null
  canvas_height?: number | null
}

export interface BoundingBoxResponse {
  x: number
  y: number
  width: number
  height: number
}

export interface PixelDiffRegionResponse {
  bounds: BoundingBoxResponse
  changed_pixel_count: number
}

export interface PixelDiffResultResponse {
  total_pixel_count: number
  changed_pixel_count: number
  diff_ratio: number
  regions: PixelDiffRegionResponse[]
  risk_level: string
}

export interface LayoutElementChangeResponse {
  element_id: string
  change_type: string
  baseline_bounds?: BoundingBoxResponse | null
  current_bounds?: BoundingBoxResponse | null
  detail: string
}

export interface LayoutDiffResultResponse {
  changes: LayoutElementChangeResponse[]
  risk_level: string
}

export interface LayoutConsistencyIssueResponse {
  issue_type: string
  element_ids: string[]
  detail: string
  risk_level: string
}

export interface VisualRegressionFindingResponse {
  category: string
  risk_level: string
  message: string
  element_id?: string | null
}

export interface VisualComparisonReportResponse {
  project_id: string
  baseline_label: string
  current_label: string
  generated_at: string
  pixel_diff?: PixelDiffResultResponse | null
  layout_diff?: LayoutDiffResultResponse | null
  consistency_issues: LayoutConsistencyIssueResponse[]
  findings: VisualRegressionFindingResponse[]
  verdict: string
  summary: string
}

// ---- memory_schemas.py ----

export interface MemoryRecallRequest {
  query_text: string
  top_k?: number
  record_type?: string | null
}

export interface MemoryRecordResponse {
  record_id: string
  project_id: string
  record_type: string
  recorded_at: string
  summary: string
  payload: Record<string, unknown>
  health_score?: number | null
}

export interface MemoryRecallMatchResponse {
  record: MemoryRecordResponse
  similarity_score: number
}

export interface MemoryHistoryResponse {
  records: MemoryRecordResponse[]
}

export interface HealthScoreTrendResponse {
  health_scores: number[]
}
