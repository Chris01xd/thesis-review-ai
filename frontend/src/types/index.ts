export type Role = 'ADMIN' | 'COORDINATOR' | 'ADVISOR' | 'STUDENT'

export interface User {
  id: number
  name: string
  email: string
  role: Role
  program_id: number | null
  advisor_id: number | null
  program?: string
  advisor?: string
  orcid_id?: string
  affiliation?: string
  expertise?: string
  created_at?: string
}

export interface Program {
  id: number
  name: string
}

export interface Advance {
  id: number
  student_id: number
  advisor_id: number
  title: string
  advance_type: string
  version: number
  status: AdvanceStatus
  filename: string
  page_count: number | null
  created_at: string
  overall_score?: number | null
  grade?: number | null
  total_findings?: number
  findings_pending?: number
  student_name?: string
  advisor_name?: string
  program_name?: string
}

export type AdvanceStatus =
  | 'Pendiente'
  | 'Análisis IA en proceso'
  | 'En revisión humana'
  | 'Observado'
  | 'Aprobado'
  | 'Rechazado'

export interface AIAnalysis {
  id: number
  advance_id: number
  structure_score: number
  content_score: number
  form_score: number
  originality_score: number
  overall_score: number
  grade: number
  executive_summary: string
  model_used: string
  processing_ms: number
  created_at: string
}

export type Severity = 'Crítico' | 'Mayor' | 'Advertencia' | 'Menor' | 'Sugerencia'

export interface Finding {
  id: number
  type: string
  section_ref: string
  page_ref: number | null
  severity: Severity
  description: string
  correction_steps: string
  example_improvement: string
  recommendation: string
  human_action: string | null
  human_comment: string | null
}

export interface Citation {
  id: number
  raw_reference: string
  title: string | null
  year: string | null
  doi: string | null
  status: 'Con DOI' | 'No encontrada' | 'Pendiente'
  source: string | null
  suggestion: string | null
}

export interface SimilarityResult {
  id: number
  similarity: number
  section_ref: string
  status: string
  compared_title: string | null
}

export interface Template {
  id: number
  program_id: number
  name: string
  version: string
  content: string
  expected_sections: string
  rubric_json: string
  active: number
  program_name?: string
}

export interface AuditLog {
  id: number
  user_id: number
  action: string
  resource: string
  resource_id: number | null
  details: string | null
  created_at: string
  user_name?: string
}

export interface GradePoint {
  id: number
  title: string
  version: number
  grade: number | null
  overall_score: number | null
  created_at: string
}

export interface DashboardSummary {
  student: User
  latest: Advance | null
  summary: {
    total_advances: number
    pending_findings: number
    last_grade: number | null
    last_score: number | null
  }
}

export interface Stats {
  total_students: number
  total_advances: number
  advances_pending: number
  advances_approved: number
  advances_rejected: number
  avg_grade: number | null
  avg_score: number | null
  findings_by_severity: { severity: string; count: number }[]
  advances_by_status: { status: string; count: number }[]
  grades_distribution: { range: string; count: number }[]
}
