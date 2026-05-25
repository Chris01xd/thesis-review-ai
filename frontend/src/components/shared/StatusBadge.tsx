import type { AdvanceStatus } from '@/types'
import { cn } from '@/lib/utils'

const config: Record<AdvanceStatus, string> = {
  'Pendiente':              'bg-slate-100 text-slate-700',
  'Análisis IA en proceso': 'bg-orange-100 text-orange-800',
  'En revisión humana':     'bg-blue-100 text-blue-800',
  'Observado':              'bg-amber-100 text-amber-800',
  'Aprobado':               'bg-emerald-100 text-emerald-800',
  'Rechazado':              'bg-red-100 text-red-800',
}

export function StatusBadge({ status }: { status: AdvanceStatus }) {
  return (
    <span className={cn('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium', config[status] ?? config.Pendiente)}>
      {status}
    </span>
  )
}
