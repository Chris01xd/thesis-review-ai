import { cn } from '@/lib/utils'

interface ProgressProps {
  value: number
  className?: string
  color?: string
}

export function Progress({ value, className, color = 'bg-blue-600' }: ProgressProps) {
  const pct = Math.min(Math.max(value, 0), 100)
  return (
    <div className={cn('w-full bg-slate-200 rounded-full h-2 overflow-hidden', className)}>
      <div
        className={cn('h-full rounded-full transition-all', color)}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}
