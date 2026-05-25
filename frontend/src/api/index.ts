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
  client.post<{ message: string }>(`/api/advance/${id}/analyze`).then((r) => r.data)

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
