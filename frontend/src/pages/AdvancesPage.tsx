import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { getAdvances, getStudentAdvances } from '@/api'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { LoadingSpinner, PageError } from '@/components/shared/LoadingSpinner'
import { formatDate, gradeColor } from '@/lib/utils'
import { Search, Eye } from 'lucide-react'

export default function AdvancesPage() {
  const { user } = useAuth()
  const [searchParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  const studentIdParam = searchParams.get('student_id')

  const { data, isLoading, error } = useQuery({
    queryKey: ['advances', user?.role, user?.id, studentIdParam],
    queryFn: () => {
      if (user?.role === 'STUDENT') return getStudentAdvances(user.id)
      if (studentIdParam) return getAdvances({ student_id: studentIdParam })
      return getAdvances()
    },
  })

  const filtered = data?.filter((a) => {
    const matchSearch = `${a.title} ${a.advance_type} ${a.student_name ?? ''}`.toLowerCase().includes(search.toLowerCase())
    const matchStatus = !statusFilter || a.status === statusFilter
    return matchSearch && matchStatus
  })

  const statuses = ['Pendiente', 'Análisis IA en proceso', 'En revisión humana', 'Observado', 'Aprobado', 'Rechazado']

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Avances de Tesis</h1>
        <p className="text-slate-500 text-sm mt-1">
          {studentIdParam ? `Avances del estudiante #${studentIdParam}` : 'Todos los avances registrados'}
        </p>
      </div>

      <Card>
        <div className="p-4 border-b border-slate-100 flex flex-wrap gap-3">
          <div className="relative flex-1 min-w-48">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <Input placeholder="Buscar..." className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-52">
            <option value="">Todos los estados</option>
            {statuses.map((s) => <option key={s} value={s}>{s}</option>)}
          </Select>
        </div>

        {isLoading && <LoadingSpinner />}
        {error && <PageError message="Error al cargar avances" />}

        {filtered && (
          <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>#</TableHead>
                <TableHead>Título</TableHead>
                {user?.role !== 'STUDENT' && <TableHead>Estudiante</TableHead>}
                <TableHead>Tipo</TableHead>
                <TableHead>Versión</TableHead>
                <TableHead>Nota IA</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Fecha</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={9} className="text-center text-slate-400 py-10">
                    No se encontraron avances
                  </TableCell>
                </TableRow>
              )}
              {filtered.map((adv) => (
                <TableRow key={adv.id}>
                  <TableCell className="text-slate-400">{adv.id}</TableCell>
                  <TableCell className="max-w-xs">
                    <Link to={`/advances/${adv.id}`} className="font-medium text-slate-800 hover:text-blue-700 line-clamp-2">
                      {adv.title}
                    </Link>
                  </TableCell>
                  {user?.role !== 'STUDENT' && (
                    <TableCell className="text-slate-600">{adv.student_name ?? '—'}</TableCell>
                  )}
                  <TableCell>
                    <Badge variant="gray">{adv.advance_type}</Badge>
                  </TableCell>
                  <TableCell className="text-slate-500">v{adv.version}</TableCell>
                  <TableCell>
                    {adv.grade !== null && adv.grade !== undefined ? (
                      <span className={`font-bold ${gradeColor(adv.grade)}`}>{adv.grade}/20</span>
                    ) : <span className="text-slate-300">—</span>}
                  </TableCell>
                  <TableCell><StatusBadge status={adv.status} /></TableCell>
                  <TableCell className="text-slate-400 text-xs">{formatDate(adv.created_at)}</TableCell>
                  <TableCell>
                    <Link to={`/advances/${adv.id}`} className="p-1.5 rounded hover:bg-slate-100 text-slate-500 inline-flex">
                      <Eye size={16} />
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          </div>
        )}
      </Card>
    </div>
  )
}
