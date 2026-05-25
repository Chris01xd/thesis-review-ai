import type { Severity } from '@/types'
import { cn } from '@/lib/utils'

const config: Record<Severity, { label: string; className: string }> = {
  Crítico:     { label: 'Crítico',     className: 'bg-red-100 text-red-800 border-red-200' },
  Mayor:       { label: 'Mayor',       className: 'bg-orange-100 text-orange-800 border-orange-200' },
  Advertencia: { label: 'Advertencia', className: 'bg-yellow-100 text-yellow-800 border-yellow-200' },
  Menor:       { label: 'Menor',       className: 'bg-blue-100 text-blue-800 border-blue-200' },
  Sugerencia:  { label: 'Sugerencia',  className: 'bg-slate-100 text-slate-600 border-slate-200' },
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  const c = config[severity] ?? config.Sugerencia
  return (
    <span className={cn('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border', c.className)}>
      {c.label}
    </span>
  )
}
