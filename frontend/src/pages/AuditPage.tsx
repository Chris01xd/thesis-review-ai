import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getAuditLogs } from '@/api'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { formatDateTime } from '@/lib/utils'
import { Search } from 'lucide-react'

const ACTION_COLOR: Record<string, 'success' | 'error' | 'info' | 'warning' | 'gray'> = {
  LOGIN: 'success', LOGOUT: 'gray', UPLOAD: 'info', AI_ANALYSIS: 'info',
  HUMAN_REVIEW_CLOSED: 'success', DELETE: 'error', CREATE_USER: 'info',
  UPDATE_USER: 'warning', TEMPLATE_SAVE: 'info',
}

export default function AuditPage() {
  const [search, setSearch] = useState('')
  const { data, isLoading } = useQuery({ queryKey: ['audit'], queryFn: () => getAuditLogs({ limit: 200 }) })

  const filtered = data?.filter((l) =>
    `${l.user_name ?? ''} ${l.action} ${l.resource} ${l.details ?? ''}`.toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Auditoría</h1>
        <p className="text-slate-500 text-sm mt-1">Registro de todas las acciones del sistema</p>
      </div>

      <Card>
        <div className="p-4 border-b border-slate-100">
          <div className="relative max-w-sm">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <Input placeholder="Buscar en logs..." className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
        </div>

        {isLoading && <LoadingSpinner />}

        {filtered && (
          <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Fecha</TableHead>
                <TableHead>Usuario</TableHead>
                <TableHead>Acción</TableHead>
                <TableHead>Recurso</TableHead>
                <TableHead>Detalles</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-slate-400 py-10">Sin registros</TableCell>
                </TableRow>
              )}
              {filtered.map((log) => (
                <TableRow key={log.id}>
                  <TableCell className="text-xs text-slate-400 whitespace-nowrap">{formatDateTime(log.created_at)}</TableCell>
                  <TableCell className="text-slate-700 font-medium">{log.user_name ?? `#${log.user_id}`}</TableCell>
                  <TableCell>
                    <Badge variant={ACTION_COLOR[log.action] ?? 'gray'}>{log.action}</Badge>
                  </TableCell>
                  <TableCell className="text-slate-500">
                    {log.resource}{log.resource_id ? ` #${log.resource_id}` : ''}
                  </TableCell>
                  <TableCell className="text-xs text-slate-400 max-w-xs truncate">
                    {log.details ?? '—'}
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
