import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/contexts/AuthContext'
import { getStudentDashboard, getStats, getAdvances } from '@/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { formatDate, gradeColor, scoreColor } from '@/lib/utils'
import { Link } from 'react-router-dom'
import { FileText, CheckCircle2, AlertTriangle, TrendingUp, Users, Clock } from 'lucide-react'
import type { Role } from '@/types'

export default function DashboardPage() {
  const { user } = useAuth()
  if (!user) return null

  if (user.role === 'STUDENT') return <StudentDashboard studentId={user.id} />
  return <AdminDashboard role={user.role} />
}

function StudentDashboard({ studentId }: { studentId: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ['student-dashboard', studentId],
    queryFn: () => getStudentDashboard(studentId),
  })

  if (isLoading) return <LoadingSpinner />
  if (!data) return null

  const { student, latest, summary } = data

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Bienvenido, {student.name}</h1>
        <p className="text-slate-500 text-sm mt-1">{student.program} · Asesor: {student.advisor ?? '—'}</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard icon={<FileText />} label="Total avances" value={summary.total_advances} color="blue" />
        <StatCard
          icon={<TrendingUp />} label="Última nota"
          value={summary.last_grade != null ? `${summary.last_grade}/20` : '—'}
          color={summary.last_grade != null && summary.last_grade >= 14 ? 'green' : 'amber'}
        />
        <StatCard
          icon={<TrendingUp />} label="Puntaje IA"
          value={summary.last_score != null ? `${Math.round(summary.last_score)}%` : '—'}
          color="purple"
        />
        <StatCard icon={<AlertTriangle />} label="Hallazgos pendientes" value={summary.pending_findings} color="red" />
      </div>

      {/* Latest advance */}
      {latest && (
        <Card>
          <CardHeader>
            <CardTitle>Último avance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-start justify-between flex-wrap gap-3">
              <div>
                <p className="font-medium text-slate-800">{latest.title}</p>
                <p className="text-sm text-slate-500 mt-1">
                  {latest.advance_type} · v{latest.version} · {formatDate(latest.created_at)}
                </p>
              </div>
              <StatusBadge status={latest.status} />
            </div>
            {latest.overall_score != null && (
              <div className="mt-4">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-600">Puntaje IA</span>
                  <span className={scoreColor(latest.overall_score ?? null)}>{Math.round(latest.overall_score)}%</span>
                </div>
                <Progress value={latest.overall_score} />
              </div>
            )}
            <div className="mt-4">
              <Link to={`/advances/${latest.id}`} className="text-sm text-blue-600 hover:underline font-medium">
                Ver detalle completo →
              </Link>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function AdminDashboard({ role }: { role: Role }) {
  const { data: stats, isLoading: loadingStats } = useQuery({
    queryKey: ['stats'],
    queryFn: () => getStats(),
  })
  const { data: advances, isLoading: loadingAdv } = useQuery({
    queryKey: ['advances', { limit: 5 }],
    queryFn: () => getAdvances({ limit: 5 }),
  })

  if (loadingStats || loadingAdv) return <LoadingSpinner />

  const roleLabel: Record<Role, string> = {
    ADMIN: 'Administrador', COORDINATOR: 'Coordinador', ADVISOR: 'Asesor', STUDENT: 'Estudiante',
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Dashboard</h1>
        <p className="text-slate-500 text-sm mt-1">Panel de control · {roleLabel[role]}</p>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 mb-6">
          <StatCard icon={<Users />} label="Estudiantes" value={stats.total_students} color="blue" />
          <StatCard icon={<FileText />} label="Total avances" value={stats.total_advances} color="purple" />
          <StatCard icon={<Clock />} label="Pendientes" value={stats.advances_pending} color="amber" />
          <StatCard icon={<CheckCircle2 />} label="Aprobados" value={stats.advances_approved} color="green" />
        </div>
      )}

      {/* Average row */}
      {stats && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 md:gap-4 mb-6">
          <Card>
            <CardContent className="pt-4">
              <p className="text-sm text-slate-500 mb-1">Promedio de nota (IA)</p>
              <p className={`text-3xl font-bold ${gradeColor(stats.avg_grade)}`}>
                {stats.avg_grade !== null ? stats.avg_grade.toFixed(1) : '—'} <span className="text-base font-normal text-slate-400">/20</span>
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <p className="text-sm text-slate-500 mb-1">Puntaje promedio (IA)</p>
              <p className={`text-3xl font-bold ${scoreColor(stats.avg_score)}`}>
                {stats.avg_score !== null ? Math.round(stats.avg_score) : '—'} <span className="text-base font-normal text-slate-400">%</span>
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Recent advances */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Avances recientes</CardTitle>
            <Link to="/advances" className="text-sm text-blue-600 hover:underline">Ver todos</Link>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {advances?.length === 0 && (
            <p className="text-sm text-slate-500 text-center py-8">No hay avances registrados</p>
          )}
          {advances?.map((adv) => (
            <div key={adv.id} className="flex flex-col sm:flex-row sm:items-center sm:justify-between px-4 sm:px-5 py-3 border-b last:border-0 hover:bg-slate-50 gap-1.5 sm:gap-3">
              <div className="min-w-0">
                <Link to={`/advances/${adv.id}`} className="text-sm font-medium text-slate-800 hover:text-blue-700 line-clamp-1">
                  {adv.title}
                </Link>
                <p className="text-xs text-slate-400 mt-0.5">{formatDate(adv.created_at)}</p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {adv.grade !== null && adv.grade !== undefined && (
                  <Badge variant="gray">{adv.grade}/20</Badge>
                )}
                <StatusBadge status={adv.status} />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

function StatCard({
  icon, label, value, color,
}: {
  icon: React.ReactNode
  label: string
  value: number | string
  color: 'blue' | 'green' | 'amber' | 'red' | 'purple'
}) {
  const colors = {
    blue:   'bg-blue-50 text-blue-600',
    green:  'bg-emerald-50 text-emerald-600',
    amber:  'bg-amber-50 text-amber-600',
    red:    'bg-red-50 text-red-600',
    purple: 'bg-purple-50 text-purple-600',
  }
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${colors[color]}`}>{icon}</div>
          <div>
            <p className="text-xs text-slate-500">{label}</p>
            <p className="text-xl font-bold text-slate-800">{value}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
