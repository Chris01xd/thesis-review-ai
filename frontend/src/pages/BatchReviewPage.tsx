import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getAdvances, analyzeAdvance } from '@/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input, Select } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { formatDate, gradeColor } from '@/lib/utils'
import { cn } from '@/lib/utils'
import { Search, Play, CheckSquare, Square, CheckCircle2, XCircle, RotateCcw, ExternalLink } from 'lucide-react'
import type { Advance } from '@/types'

type JobStatus = 'idle' | 'pending' | 'done' | 'error'

interface JobResult {
  id: number
  title: string
  status: JobStatus
  error?: string
}

export default function BatchReviewPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [running, setRunning] = useState(false)
  const [jobs, setJobs] = useState<JobResult[]>([])
  const [progress, setProgress] = useState(0)
  const [done, setDone] = useState(false)

  const { data: advances, isLoading } = useQuery({
    queryKey: ['advances-batch'],
    queryFn: () => getAdvances({ limit: 500 }),
    refetchOnWindowFocus: false,
  })

  const filtered = advances?.filter((a) => {
    const matchSearch = `${a.title} ${a.student_name ?? ''} ${a.advance_type}`.toLowerCase().includes(search.toLowerCase())
    const matchStatus = !statusFilter || a.status === statusFilter
    return matchSearch && matchStatus
  }) ?? []

  const allIds = filtered.map((a) => a.id)
  const allSelected = allIds.length > 0 && allIds.every((id) => selected.has(id))

  function toggleAll() {
    if (allSelected) {
      setSelected((prev) => {
        const next = new Set(prev)
        allIds.forEach((id) => next.delete(id))
        return next
      })
    } else {
      setSelected((prev) => new Set([...prev, ...allIds]))
    }
  }

  function toggleOne(id: number) {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  async function runBatch() {
    if (selected.size === 0) return
    setRunning(true)
    setDone(false)
    setProgress(0)

    const ids = [...selected]
    const results: JobResult[] = ids.map((id) => ({
      id,
      title: advances?.find((a) => a.id === id)?.title ?? `Avance #${id}`,
      status: 'pending',
    }))
    setJobs(results)

    for (let i = 0; i < ids.length; i++) {
      const id = ids[i]
      try {
        await analyzeAdvance(id)
        setJobs((prev) => prev.map((j) => j.id === id ? { ...j, status: 'done' } : j))
      } catch (e) {
        const msg = e instanceof Error ? e.message : 'Error desconocido'
        setJobs((prev) => prev.map((j) => j.id === id ? { ...j, status: 'error', error: msg } : j))
      }
      setProgress(Math.round(((i + 1) / ids.length) * 100))
    }

    setRunning(false)
    setDone(true)
  }

  function reset() {
    setSelected(new Set())
    setJobs([])
    setProgress(0)
    setDone(false)
  }

  const doneCount = jobs.filter((j) => j.status === 'done').length
  const errorCount = jobs.filter((j) => j.status === 'error').length
  const statuses = ['Pendiente', 'Análisis IA en proceso', 'En revisión humana', 'Observado', 'Aprobado', 'Rechazado']

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Revisión por Lotes</h1>
        <p className="text-slate-500 text-sm mt-1">Selecciona múltiples avances y ejecuta el análisis IA en secuencia</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-6">
        {/* Left: Selection panel */}
        <div className="lg:col-span-2">
          <Card>
            <div className="p-4 border-b border-slate-100 flex flex-wrap gap-3 items-center">
              <div className="relative flex-1 min-w-40">
                <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <Input placeholder="Buscar avance..." className="pl-9 h-9 text-sm" value={search} onChange={(e) => setSearch(e.target.value)} />
              </div>
              <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-48 h-9 text-sm">
                <option value="">Todos los estados</option>
                {statuses.map((s) => <option key={s} value={s}>{s}</option>)}
              </Select>
              <button
                onClick={toggleAll}
                disabled={running}
                className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-800 disabled:opacity-40"
              >
                {allSelected ? <CheckSquare size={16} /> : <Square size={16} />}
                {allSelected ? 'Quitar todos' : 'Selec. todos'}
              </button>
            </div>

            {isLoading && <LoadingSpinner />}

            {!isLoading && filtered.length === 0 && (
              <div className="text-center text-slate-400 py-12 text-sm">No se encontraron avances</div>
            )}

            <div className="divide-y divide-slate-100 max-h-[520px] overflow-y-auto">
              {filtered.map((adv) => (
                <AdvanceRow
                  key={adv.id}
                  advance={adv}
                  checked={selected.has(adv.id)}
                  disabled={running}
                  onChange={() => toggleOne(adv.id)}
                />
              ))}
            </div>
          </Card>
        </div>

        {/* Right: Action panel */}
        <div className="space-y-4">
          {/* Selection summary */}
          <Card>
            <CardHeader><CardTitle>Selección</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">Avances seleccionados</span>
                <span className="text-2xl font-bold text-blue-700">{selected.size}</span>
              </div>
              <div className="flex items-center justify-between text-sm text-slate-500">
                <span>Total disponibles</span>
                <span>{filtered.length}</span>
              </div>
              {selected.size > 0 && !running && !done && (
                <Button onClick={runBatch} className="w-full" disabled={selected.size === 0}>
                  <Play size={15} />
                  Iniciar análisis IA
                </Button>
              )}
              {(running || done) && (
                <Button variant="outline" onClick={reset} className="w-full" disabled={running}>
                  <RotateCcw size={15} />
                  Nueva selección
                </Button>
              )}
              {selected.size === 0 && !running && !done && (
                <p className="text-xs text-slate-400 text-center">Selecciona al menos un avance</p>
              )}
            </CardContent>
          </Card>

          {/* Progress / Results */}
          {(running || done) && (
            <Card>
              <CardHeader>
                <CardTitle>{done ? 'Resultado' : 'Procesando…'}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Progress bar */}
                <div>
                  <div className="flex justify-between text-xs text-slate-500 mb-1">
                    <span>{progress}%</span>
                    <span>{jobs.filter((j) => j.status !== 'pending').length}/{jobs.length}</span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-2.5 overflow-hidden">
                    <div
                      className={cn('h-full rounded-full transition-all duration-300', done && errorCount === 0 ? 'bg-emerald-500' : done ? 'bg-amber-500' : 'bg-blue-600')}
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>

                {/* Summary */}
                {done && (
                  <div className="flex gap-3">
                    <div className="flex-1 bg-emerald-50 rounded-lg p-3 text-center">
                      <CheckCircle2 size={20} className="mx-auto text-emerald-600 mb-1" />
                      <p className="text-xl font-bold text-emerald-700">{doneCount}</p>
                      <p className="text-xs text-emerald-600">Exitosos</p>
                    </div>
                    {errorCount > 0 && (
                      <div className="flex-1 bg-red-50 rounded-lg p-3 text-center">
                        <XCircle size={20} className="mx-auto text-red-500 mb-1" />
                        <p className="text-xl font-bold text-red-600">{errorCount}</p>
                        <p className="text-xs text-red-500">Con error</p>
                      </div>
                    )}
                  </div>
                )}

                {/* Job list */}
                <div className="space-y-1.5 max-h-64 overflow-y-auto">
                  {jobs.map((job) => (
                    <div key={job.id} className="flex items-center gap-2 text-xs">
                      {job.status === 'pending' && <div className="w-3.5 h-3.5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin shrink-0" />}
                      {job.status === 'done'    && <CheckCircle2 size={14} className="text-emerald-500 shrink-0" />}
                      {job.status === 'error'   && <XCircle size={14} className="text-red-500 shrink-0" />}
                      <span className={cn('flex-1 truncate', job.status === 'error' ? 'text-red-600' : 'text-slate-600')}>
                        {job.title}
                      </span>
                      {job.status === 'done' && (
                        <Link to={`/advances/${job.id}`} className="text-blue-500 hover:text-blue-700 shrink-0">
                          <ExternalLink size={12} />
                        </Link>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Info box */}
          {!running && !done && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-xs text-blue-700 space-y-1">
              <p className="font-semibold">¿Qué hace el análisis IA?</p>
              <ul className="list-disc list-inside space-y-0.5 text-blue-600">
                <li>Evalúa estructura, contenido, forma y originalidad</li>
                <li>Genera hallazgos con severidad y correcciones</li>
                <li>Detecta similitud interna (plagio)</li>
                <li>Valida referencias bibliográficas</li>
                <li>Asigna nota automática (0-20)</li>
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function AdvanceRow({
  advance, checked, disabled, onChange,
}: {
  advance: Advance
  checked: boolean
  disabled: boolean
  onChange: () => void
}) {
  return (
    <label className={cn(
      'flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors select-none',
      checked ? 'bg-blue-50' : 'hover:bg-slate-50',
      disabled && 'cursor-not-allowed opacity-60',
    )}>
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        disabled={disabled}
        className="w-4 h-4 rounded text-blue-600 shrink-0"
      />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-800 truncate">{advance.title}</p>
        <p className="text-xs text-slate-400 mt-0.5">
          {advance.student_name ?? '—'} · {advance.advance_type} v{advance.version} · {formatDate(advance.created_at)}
        </p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {advance.grade != null && (
          <span className={`text-xs font-bold ${gradeColor(advance.grade)}`}>{advance.grade}/20</span>
        )}
        <StatusBadge status={advance.status} />
        <Badge variant="gray" className="text-xs">#{advance.id}</Badge>
      </div>
    </label>
  )
}
