import client from './client'
import type {
  User, Advance, AIAnalysis, Finding, Citation, SimilarityResult,
  Template, AuditLog, GradePoint, DashboardSummary, Stats, Program,
} from '../types'

// ── Auth ──────────────────────────────────────────────────────────────────────
export const login = (email: string, password: string) =>
  client.post<{ user: User; token: string }>('/api/auth/login', { email, password })
    .then((r) => r.data)

// ── Students ──────────────────────────────────────────────────────────────────
export const getStudents = () =>
  client.get<User[]>('/api/students').then((r) => r.data)

export const getStudentDashboard = (id: number) =>
  client.get<DashboardSummary>(`/api/student/${id}/dashboard`).then((r) => r.data)

export const getStudentAdvances = (id: number) =>
  client.get<Advance[]>(`/api/student/${id}/advances`).then((r) => r.data)

export const getGradeHistory = (id: number) =>
  client.get<GradePoint[]>(`/api/student/${id}/grade-history`).then((r) => r.data)

// ── Advances ──────────────────────────────────────────────────────────────────
export const getAdvances = (params?: Record<string, string | number>) =>
  client.get<Advance[]>('/api/advances', { params }).then((r) => r.data)

export const getAdvance = (id: number) =>
  client.get<{ advance: Advance; analysis: AIAnalysis | null }>(`/api/advance/${id}`)
    .then((r) => r.data)

export const uploadAdvance = (formData: FormData) =>
  client.post<{ advance_id: number; message: string }>('/api/advance/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  }).then((r) => r.data)

export const analyzeAdvance = (id: number) =>
  client.post<{ message: string }>(`/api/advance/${id}/analyze`, {}, { timeout: 180000 }).then((r) => r.data)

// ── Findings ──────────────────────────────────────────────────────────────────
export const getFindings = (advanceId: number) =>
  client.get<Finding[]>(`/api/advance/${advanceId}/findings`).then((r) => r.data)

export const updateFinding = (id: number, data: { human_action: string; human_comment: string }) =>
  client.patch<Finding>(`/api/finding/${id}`, data).then((r) => r.data)

// ── Citations & Similarity ────────────────────────────────────────────────────
export const getCitations = (advanceId: number) =>
  client.get<Citation[]>(`/api/advance/${advanceId}/citations`).then((r) => r.data)

export const getSimilarity = (advanceId: number) =>
  client.get<SimilarityResult[]>(`/api/advance/${advanceId}/similarity`).then((r) => r.data)

// ── Stats ─────────────────────────────────────────────────────────────────────
export const getStats = (programId?: number) =>
  client.get<Stats>('/api/stats', { params: programId ? { program_id: programId } : {} })
    .then((r) => r.data)

// ── Users ─────────────────────────────────────────────────────────────────────
export const getUsers = (role?: string) =>
  client.get<User[]>('/api/users', { params: role ? { role } : {} }).then((r) => r.data)

export const createUser = (data: Partial<User> & { password: string }) =>
  client.post<User>('/api/users', data).then((r) => r.data)

export const updateUser = (id: number, data: Partial<User>) =>
  client.patch<User>(`/api/users/${id}`, data).then((r) => r.data)

export const deleteUser = (id: number) =>
  client.delete(`/api/users/${id}`).then((r) => r.data)

// ── Templates ─────────────────────────────────────────────────────────────────
export const getTemplates = () =>
  client.get<Template[]>('/api/templates').then((r) => r.data)

export const saveTemplate = (data: Partial<Template>) =>
  client.post<Template>('/api/templates', data).then((r) => r.data)

// ── Programs ──────────────────────────────────────────────────────────────────
export const getPrograms = () =>
  client.get<Program[]>('/api/programs').then((r) => r.data)

// ── Audit ─────────────────────────────────────────────────────────────────────
export const getAuditLogs = (params?: Record<string, string | number>) =>
  client.get<AuditLog[]>('/api/audit', { params }).then((r) => r.data)

// ── Similitud Académica Abierta ────────────────────────────────────────────────
export interface SimilarityFragment {
  doc_fragment: string
  source_fragment: string
  similarity: number
  source_title?: string
}
export interface SimilaritySource {
  title: string
  authors: string[]
  year: number | null
  doi: string
  url: string
  abstract: string
  source_name: string
  api: string
  similarity_score: number
  matching_fragments: SimilarityFragment[]
}
export interface SimilarityReport {
  overall_similarity: number
  risk_level: string
  risk_color: string
  total_sources_checked: number
  matching_sources: number
  sources: SimilaritySource[]
  top_fragments: SimilarityFragment[]
  document_metadata: { title: string; abstract: string; keywords: string[]; query: string }
  filename: string
  analyzed_at: string
  apis_consulted: string[]
  limitations: string[]
}

export const downloadSimilarityReport = async (report: SimilarityReport): Promise<void> => {
  const res = await client.post('/api/similitud/report', report, {
    responseType: 'blob',
    timeout: 60000,
  })
  const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
  const a   = document.createElement('a')
  a.href    = url
  a.download = `reporte_similitud_${report.filename.replace(/\.[^.]+$/, '')}.pdf`
  a.click()
  URL.revokeObjectURL(url)
}

export const checkSimilarity = async (file: File): Promise<SimilarityReport> => {
  const form = new FormData()
  form.append('file', file)
  const res = await client.post<SimilarityReport>('/api/similitud/check', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
  return res.data
}

// ── Thesis Generator ──────────────────────────────────────────────────────────
export interface ThesisRequest {
  title: string
  authors: string
  advisor: string
  research_line: string
  city: string
  year: number
  jurado?: string[]
}
export interface ThesisResult {
  uid: string
  pdf_file: string
  docx_file: string
  source: 'openai' | 'template'
  sections: Record<string, string | string[]>
}

export const generateThesis = (data: ThesisRequest) =>
  client.post<ThesisResult>('/api/generar_tesis', data, { timeout: 120000 }).then((r) => r.data)

export const downloadThesisFile = async (filename: string) => {
  const res = await client.get(`/api/generar_tesis/download/${filename}`, {
    responseType: 'blob',
  })
  const ext = filename.endsWith('.pdf') ? 'pdf' : 'docx'
  const mime = ext === 'pdf'
    ? 'application/pdf'
    : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  const url = URL.createObjectURL(new Blob([res.data], { type: mime }))
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
  return url
}

export const getThesisPdfBlob = async (filename: string): Promise<string> => {
  const res = await client.get(`/api/generar_tesis/download/${filename}`, {
    responseType: 'blob',
  })
  return URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
}

// ── Detector IA ───────────────────────────────────────────────────────────────
export interface AIParaMetrics {
  sentence_cv: number
  ttr: number
  ngram_repetition: number
  bigram_entropy: number
  formal_words: number
  avg_sentence_len: number
}
export interface AIParagraph {
  text: string
  score: number
  metrics: AIParaMetrics
}
export interface AIGlobalMetrics {
  sentence_cv: number
  paragraph_cv: number
  type_token_ratio: number
  ngram_repetition: number
  bigram_entropy: number
  formal_word_ratio: number
  avg_sentence_len: number
}
export interface AIDetectionReport {
  ai_probability: number
  statistical_score: number
  hf_score: number | null
  hf_model_used: string | null
  risk_level: string
  risk_color: string
  low_confidence: boolean
  total_words: number
  total_sentences: number
  total_paragraphs: number
  suspicious_count: number
  suspicious_paragraphs: AIParagraph[]
  all_paragraphs: AIParagraph[]
  global_metrics: AIGlobalMetrics
  methods_used: string[]
  filename: string
  analyzed_at: string
  elapsed_s: number
  disclaimer: string
  limitations: string[]
}

export const downloadAIDetectionReport = async (report: AIDetectionReport): Promise<void> => {
  const res = await client.post('/api/ai-detector/report', report, {
    responseType: 'blob',
    timeout: 60000,
  })
  const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
  const a   = document.createElement('a')
  a.href    = url
  a.download = `reporte_detector_ia_${(report.filename || 'documento').replace(/\.[^.]+$/, '')}.pdf`
  a.click()
  URL.revokeObjectURL(url)
}

export const checkAIContent = async (file: File): Promise<AIDetectionReport> => {
  const form = new FormData()
  form.append('file', file)
  const res = await client.post<AIDetectionReport>('/api/ai-detector/check', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180000,
  })
  return res.data
}

// ── Reports ───────────────────────────────────────────────────────────────────
export const downloadReport = async (advanceId: number) => {
  const res = await client.get(`/api/advance/${advanceId}/report`, {
    responseType: 'blob',
  })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = `reporte_avance_${advanceId}.pdf`
  a.click()
  URL.revokeObjectURL(url)
}
