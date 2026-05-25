import { cn } from '@/lib/utils'

interface ScoreRingProps {
  value: number | null
  label: string
  size?: 'sm' | 'md' | 'lg'
}

function colorFor(v: number) {
  if (v >= 80) return { stroke: '#10b981' }
  if (v >= 60) return { stroke: '#3b82f6' }
  if (v >= 40) return { stroke: '#f59e0b' }
  return { stroke: '#ef4444' }
}

const sizes = {
  sm: { r: 28, cx: 32, size: 64, fontSize: 12, label: 10 },
  md: { r: 36, cx: 44, size: 88, fontSize: 16, label: 11 },
  lg: { r: 44, cx: 52, size: 104, fontSize: 20, label: 12 },
}

export function ScoreRing({ value, label, size = 'md' }: ScoreRingProps) {
  const { r, cx, size: svgSize, fontSize } = sizes[size]
  const circumference = 2 * Math.PI * r
  const pct = value ?? 0
  const offset = circumference - (pct / 100) * circumference
  const { stroke } = colorFor(pct)

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={svgSize} height={svgSize} viewBox={`0 0 ${svgSize} ${svgSize}`}>
        <circle cx={cx} cy={cx} r={r} fill="none" stroke="#e2e8f0" strokeWidth="6" />
        <circle
          cx={cx} cy={cx} r={r}
          fill="none" stroke={stroke} strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${cx} ${cx})`}
        />
        <text x={cx} y={cx} textAnchor="middle" dominantBaseline="central"
          fontSize={fontSize} fontWeight="700" fill={stroke}>
          {value !== null ? `${Math.round(pct)}` : '—'}
        </text>
      </svg>
      <span className={cn('text-xs font-medium text-slate-600')}>{label}</span>
    </div>
  )
}
