import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getAdvances, downloadReport } from '@/api'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { formatDate, gradeColor } from '@/lib/utils'
import { Download, Search, FileDown } from 'lucide-react'

export default function ReportsPage() {
  const [search, setSearch] = useState('')
  const { data, isLoading } = useQuery({ queryKey: ['advances-all'], queryFn: () => getAdvances() })

  const downloadMut = useMutation({ mutationFn: (id: number) => downloadReport(id) })

  const filtered = data?.filter((a) =>
    `${a.title} ${a.student_name ?? ''} ${a.status}`.toLowerCase().includes(search.toLowerCase()),
  ).filter((a) => a.status !== 'Pendiente' && a.status !== 'Análisis IA en proceso')

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Reportes</h1>
        <p className="text-slate-500 text-sm mt-1">Descarga actas y reportes PDF de los avances revisados</p>
      </div>

      <Card>
        <div className="p-4 border-b border-slate-100">
          <div className="relative max-w-sm">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <Input placeholder="Buscar avance..." className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
        </div>

        {isLoading && <LoadingSpinner />}

        {filtered && (
          <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>#</TableHead>
                <TableHead>Título</TableHead>
                <TableHead>Estudiante</TableHead>
                <TableHead>Nota IA</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Fecha</TableHead>
                <TableHead>Acción</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-slate-400 py-10">
                    No hay avances con reporte disponible
                  </TableCell>
                </TableRow>
              )}
              {filtered.map((adv) => (
                <TableRow key={adv.id}>
                  <TableCell className="text-slate-400">{adv.id}</TableCell>
                  <TableCell className="max-w-xs">
                    <p className="font-medium text-slate-800 line-clamp-2">{adv.title}</p>
                    <p className="text-xs text-slate-400">{adv.advance_type} v{adv.version}</p>
                  </TableCell>
                  <TableCell className="text-slate-600">{adv.student_name ?? '—'}</TableCell>
                  <TableCell>
                    {adv.grade !== null && adv.grade !== undefined ? (
                      <span className={`font-bold ${gradeColor(adv.grade)}`}>{adv.grade}/20</span>
                    ) : <span className="text-slate-300">—</span>}
                  </TableCell>
                  <TableCell><StatusBadge status={adv.status} /></TableCell>
                  <TableCell className="text-slate-400 text-xs">{formatDate(adv.created_at)}</TableCell>
                  <TableCell>
                    <Button
                      size="sm" variant="outline"
                      loading={downloadMut.isPending && downloadMut.variables === adv.id}
                      onClick={() => downloadMut.mutate(adv.id)}
                    >
                      <FileDown size={14} /> PDF
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          </div>
        )}
      </Card>

      <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-xl">
        <div className="flex items-start gap-3">
          <Download size={20} className="text-blue-600 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-blue-800">Reportes individuales</p>
            <p className="text-xs text-blue-600 mt-1">
              Haz clic en "PDF" para descargar el acta de revisión de cada avance.
              Los reportes incluyen el análisis IA completo, hallazgos y recomendaciones.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
