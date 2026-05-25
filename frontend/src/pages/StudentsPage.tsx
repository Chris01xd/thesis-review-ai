import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getStudents } from '@/api'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { LoadingSpinner, PageError } from '@/components/shared/LoadingSpinner'
import { Search, User } from 'lucide-react'

export default function StudentsPage() {
  const [search, setSearch] = useState('')
  const { data, isLoading, error } = useQuery({ queryKey: ['students'], queryFn: getStudents })

  const filtered = data?.filter((s) =>
    `${s.name} ${s.email} ${s.program ?? ''} ${s.advisor ?? ''}`.toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Estudiantes</h1>
        <p className="text-slate-500 text-sm mt-1">Listado de estudiantes registrados en el sistema</p>
      </div>

      <Card>
        <div className="p-4 border-b border-slate-100">
          <div className="relative max-w-sm">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <Input
              placeholder="Buscar estudiante..."
              className="pl-9"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        {isLoading && <LoadingSpinner />}
        {error && <PageError message="Error al cargar estudiantes" />}

        {filtered && (
          <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>#</TableHead>
                <TableHead>Nombre</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Programa</TableHead>
                <TableHead>Asesor</TableHead>
                <TableHead>Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-slate-400 py-10">
                    No se encontraron estudiantes
                  </TableCell>
                </TableRow>
              )}
              {filtered.map((s) => (
                <TableRow key={s.id}>
                  <TableCell className="text-slate-400">{s.id}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold">
                        {s.name.charAt(0)}
                      </div>
                      <span className="font-medium text-slate-800">{s.name}</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-slate-500">{s.email}</TableCell>
                  <TableCell className="text-slate-600">{s.program ?? '—'}</TableCell>
                  <TableCell className="text-slate-600">{s.advisor ?? '—'}</TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Link
                        to={`/students/${s.id}`}
                        className="text-xs text-blue-600 hover:underline font-medium"
                      >
                        <User size={14} className="inline mr-1" />Dashboard
                      </Link>
                      <Link
                        to={`/advances?student_id=${s.id}`}
                        className="text-xs text-slate-500 hover:underline"
                      >
                        Avances
                      </Link>
                    </div>
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
