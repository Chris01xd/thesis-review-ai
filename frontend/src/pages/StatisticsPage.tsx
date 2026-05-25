import { useQuery } from '@tanstack/react-query'
import { getStats, getPrograms } from '@/api'
import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select } from '@/components/ui/input'
import { LoadingSpinner, PageError } from '@/components/shared/LoadingSpinner'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts'

const SEVERITY_COLORS: Record<string, string> = {
  'Crítico':     '#ef4444',
  'Mayor':       '#f97316',
  'Advertencia': '#f59e0b',
  'Menor':       '#3b82f6',
  'Sugerencia':  '#94a3b8',
}

const STATUS_COLORS: Record<string, string> = {
  'Pendiente':              '#94a3b8',
  'Análisis IA en proceso': '#f97316',
  'En revisión humana':     '#3b82f6',
  'Observado':              '#f59e0b',
  'Aprobado':               '#22c55e',
  'Rechazado':              '#ef4444',
}

export default function StatisticsPage() {
  const [programId, setProgramId] = useState<string>('')
  const { data: programs } = useQuery({ queryKey: ['programs'], queryFn: getPrograms })
  const { data, isLoading, error } = useQuery({
    queryKey: ['stats', programId],
    queryFn: () => getStats(programId ? Number(programId) : undefined),
  })

  return (
    <div>
      <div className="flex items-start justify-between flex-wrap gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Estadísticas</h1>
          <p className="text-slate-500 text-sm mt-1">Métricas del programa de posgrado</p>
        </div>
        <Select value={programId} onChange={(e) => setProgramId(e.target.value)} className="w-full sm:w-56">
          <option value="">Todos los programas</option>
          {programs?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </Select>
      </div>

      {isLoading && <LoadingSpinner />}
      {error && <PageError message="Error al cargar estadísticas" />}

      {data && (
        <div className="space-y-6">
          {/* KPI row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KPICard label="Estudiantes" value={data.total_students} />
            <KPICard label="Total avances" value={data.total_advances} />
            <KPICard label="Nota promedio" value={data.avg_grade !== null ? `${data.avg_grade.toFixed(1)}/20` : '—'} />
            <KPICard label="Puntaje IA prom." value={data.avg_score !== null ? `${Math.round(data.avg_score)}%` : '—'} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Advances by status */}
            <Card>
              <CardHeader><CardTitle>Avances por estado</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={260}>
                  <PieChart>
                    <Pie
                      data={data.advances_by_status}
                      dataKey="count" nameKey="status"
                      cx="50%" cy="50%" outerRadius={90}
                      label={false}
                    >
                      {data.advances_by_status.map((entry) => (
                        <Cell key={entry.status} fill={STATUS_COLORS[entry.status] ?? '#94a3b8'} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Findings by severity */}
            <Card>
              <CardHeader><CardTitle>Hallazgos por severidad</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={data.findings_by_severity} barSize={32}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="severity" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="count" name="Hallazgos" radius={[4, 4, 0, 0]}>
                      {data.findings_by_severity.map((entry) => (
                        <Cell key={entry.severity} fill={SEVERITY_COLORS[entry.severity] ?? '#94a3b8'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Grade distribution */}
            <Card className="lg:col-span-2">
              <CardHeader><CardTitle>Distribución de notas IA</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={data.grades_distribution} barSize={36}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="range" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="count" name="Avances" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}

function KPICard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <CardContent className="pt-4 pb-4">
        <p className="text-xs text-slate-500 mb-1">{label}</p>
        <p className="text-2xl font-bold text-slate-800">{value}</p>
      </CardContent>
    </Card>
  )
}
