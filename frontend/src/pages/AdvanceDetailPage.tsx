import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getAdvance, getFindings, getCitations, getSimilarity } from '@/api'
import type { AIAnalysis, SectionComparison } from '@/types'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { SeverityBadge } from '@/components/shared/SeverityBadge'
import { ScoreRing } from '@/components/shared/ScoreRing'
import { LoadingSpinner, PageError } from '@/components/shared/LoadingSpinner'
import { formatDate, gradeColor } from '@/lib/utils'
import { ArrowLeft, FileText, Brain, BookOpen, Copy, LayoutList } from 'lucide-react'
import type { Severity } from '@/types'

type Tab = 'analysis' | 'schema' | 'findings' | 'citations' | 'similarity'

export default function AdvanceDetailPage() {
  const { id } = useParams<{ id: string }>()
  const advId = Number(id)
  const [tab, setTab] = useState<Tab>('analysis')

  const { data: detail, isLoading, error } = useQuery({
    queryKey: ['advance', advId],
    queryFn: () => getAdvance(advId),
  })

  if (isLoading) return <LoadingSpinner />
  if (error || !detail) return <PageError message="No se pudo cargar el avance" />

  const { advance, analysis } = detail

  const tabs: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: 'analysis',   label: 'Análisis IA',   icon: <Brain size={15} /> },
    { key: 'schema',     label: 'Esquema',        icon: <LayoutList size={15} /> },
    { key: 'findings',   label: 'Hallazgos',     icon: <FileText size={15} /> },
    { key: 'citations',  label: 'Citas',          icon: <BookOpen size={15} /> },
    { key: 'similarity', label: 'Similitud',      icon: <Copy size={15} /> },
  ]

  return (
    <div>
      {/* Header */}
      <div className="mb-4">
        <Link to="/advances" className="text-sm text-blue-600 hover:underline flex items-center gap-1 mb-3">
          <ArrowLeft size={15} /> Volver a avances
        </Link>
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-xl font-bold text-slate-800">{advance.title}</h1>
            <p className="text-sm text-slate-500 mt-1">
              {advance.advance_type} · v{advance.version} · {formatDate(advance.created_at)}
              {advance.page_count && ` · ${advance.page_count} págs.`}
            </p>
          </div>
          <StatusBadge status={advance.status} />
        </div>
      </div>

      {/* Score cards */}
      {analysis && (
        <Card className="mb-5">
          <CardContent className="py-5">
            <div className="flex flex-wrap items-center justify-around gap-6">
              <ScoreRing value={analysis.overall_score} label="Puntaje Global" size="lg" />
              <ScoreRing value={analysis.structure_score} label="Estructura" />
              <ScoreRing value={analysis.content_score}   label="Contenido" />
              <ScoreRing value={analysis.form_score}      label="Forma" />
              <ScoreRing value={analysis.originality_score} label="Originalidad" />
              <div className="text-center">
                <div className={`text-3xl font-bold ${gradeColor(analysis.grade)}`}>
                  {analysis.grade}<span className="text-base font-normal text-slate-400">/20</span>
                </div>
                <p className="text-xs text-slate-500 mt-1">Nota IA</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-slate-200 overflow-x-auto">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-all -mb-px whitespace-nowrap ${
              tab === t.key
                ? 'border-blue-600 text-blue-700'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {t.icon}{t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'analysis'   && <AnalysisTab analysis={analysis} />}
      {tab === 'schema'     && <SchemaTab analysis={analysis} />}
      {tab === 'findings'   && <FindingsTab advId={advId} />}
      {tab === 'citations'  && <CitationsTab advId={advId} />}
      {tab === 'similarity' && <SimilarityTab advId={advId} />}
    </div>
  )
}

function AnalysisTab({ analysis }: { analysis: AIAnalysis | null }) {
  if (!analysis) return (
    <Card><CardContent className="py-10 text-center text-slate-400">Sin análisis IA disponible</CardContent></Card>
  )
  const scores = [
    { label: 'Estructura',    value: analysis.structure_score },
    { label: 'Contenido',     value: analysis.content_score },
    { label: 'Forma',         value: analysis.form_score },
    { label: 'Originalidad',  value: analysis.originality_score },
  ]
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader><CardTitle>Resumen ejecutivo</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">{analysis.executive_summary}</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Puntajes detallados</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {scores.map((s) => (
            <div key={s.label}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-600">{s.label}</span>
                <span className="font-medium text-slate-800">{Math.round(s.value)}%</span>
              </div>
              <Progress value={s.value} color={s.value >= 80 ? 'bg-emerald-500' : s.value >= 60 ? 'bg-blue-500' : s.value >= 40 ? 'bg-amber-500' : 'bg-red-500'} />
            </div>
          ))}
        </CardContent>
      </Card>
      <p className="text-xs text-slate-400">Modelo: {analysis.model_used} · Procesado en {analysis.processing_ms}ms · {formatDate(analysis.created_at)}</p>
    </div>
  )
}

function SchemaTab({ analysis }: { analysis: AIAnalysis | null }) {
  if (!analysis) return (
    <Card><CardContent className="py-10 text-center text-slate-400">Sin análisis IA disponible — ejecuta el análisis primero</CardContent></Card>
  )

  let sections: SectionComparison[] = []
  try {
    sections = analysis.section_comparison ? JSON.parse(analysis.section_comparison) : []
  } catch {
    sections = []
  }

  if (!sections.length) return (
    <Card><CardContent className="py-10 text-center text-slate-400">No hay datos de comparación de esquema disponibles</CardContent></Card>
  )

  const present  = sections.filter(s => s.present && !s.optional).length
  const optional = sections.filter(s => s.optional).length
  const missing  = sections.filter(s => !s.present).length
  const total    = sections.length
  const pct      = Math.round((present + optional) / total * 100)

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <Card>
        <CardContent className="py-4">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
            <div>
              <h3 className="font-semibold text-slate-800">Comparación con esquema institucional</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                {present + optional} de {total} secciones encontradas · {pct}% de cumplimiento estructural
              </p>
            </div>
            <div className="flex gap-3 text-sm">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block" />
                <span className="text-slate-600">Presente ({present})</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-amber-400 inline-block" />
                <span className="text-slate-600">Opcional ({optional})</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-red-500 inline-block" />
                <span className="text-slate-600">Ausente ({missing})</span>
              </span>
            </div>
          </div>
          <Progress
            value={pct}
            color={pct >= 80 ? 'bg-emerald-500' : pct >= 60 ? 'bg-blue-500' : pct >= 40 ? 'bg-amber-500' : 'bg-red-500'}
          />
        </CardContent>
      </Card>

      {/* Section checklist */}
      <Card>
        <CardContent className="p-0">
          {sections.map((s, i) => (
            <div
              key={i}
              className={`flex items-center gap-3 px-4 py-3 ${i < sections.length - 1 ? 'border-b border-slate-100' : ''} ${
                s.present && !s.optional ? 'bg-emerald-50/40' :
                s.optional ? 'bg-amber-50/40' : 'bg-red-50/40'
              }`}
            >
              <span className="text-xs text-slate-400 w-5 text-right shrink-0">{i + 1}</span>
              <span className={`text-lg shrink-0 ${s.present && !s.optional ? 'text-emerald-600' : s.optional ? 'text-amber-500' : 'text-red-500'}`}>
                {s.present && !s.optional ? '✓' : s.optional ? '◎' : '✗'}
              </span>
              <span className={`flex-1 text-sm ${s.present && !s.optional ? 'text-slate-800' : s.optional ? 'text-slate-700' : 'text-slate-800 font-medium'}`}>
                {s.section}
              </span>
              {s.optional && (
                <span className="text-xs text-amber-600 bg-amber-100 px-2 py-0.5 rounded-full shrink-0">Opcional</span>
              )}
              {!s.present && !s.optional && (
                <span className="text-xs text-red-600 bg-red-100 px-2 py-0.5 rounded-full shrink-0">Faltante</span>
              )}
            </div>
          ))}
        </CardContent>
      </Card>

      {missing > 0 && (
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="py-3">
            <p className="text-sm text-amber-800">
              <strong>{missing} sección{missing > 1 ? 'es' : ''} faltante{missing > 1 ? 's' : ''}.</strong>{' '}
              Verifica que el documento incluya estos encabezados de forma explícita o que hayas seleccionado la plantilla correcta para el tipo de avance.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function FindingsTab({ advId }: { advId: number }) {
  const { data, isLoading } = useQuery({ queryKey: ['findings', advId], queryFn: () => getFindings(advId) })
  if (isLoading) return <LoadingSpinner />
  if (!data?.length) return <Card><CardContent className="py-10 text-center text-slate-400">Sin hallazgos registrados</CardContent></Card>

  const grouped = data.reduce<Record<string, typeof data>>((acc, f) => {
    ;(acc[f.severity] ??= []).push(f)
    return acc
  }, {})
  const order: Severity[] = ['Crítico', 'Mayor', 'Advertencia', 'Menor', 'Sugerencia']

  return (
    <div className="space-y-4">
      {order.filter((s) => grouped[s]).map((sev) => (
        <div key={sev}>
          <div className="flex items-center gap-2 mb-2">
            <SeverityBadge severity={sev} />
            <span className="text-xs text-slate-500">{grouped[sev].length} hallazgo(s)</span>
          </div>
          <div className="space-y-2">
            {grouped[sev].map((f) => (
              <Card key={f.id}>
                <CardContent className="py-4">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div>
                      <Badge variant="gray" className="text-xs mb-1">{f.type}</Badge>
                      {f.section_ref && <span className="text-xs text-slate-400 ml-2">§ {f.section_ref}</span>}
                    </div>
                    {f.human_action && (
                      <Badge variant={f.human_action === 'Aceptado' ? 'success' : f.human_action === 'Rechazado' ? 'error' : 'gray'}>
                        {f.human_action}
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-slate-800 mb-2">{f.description}</p>
                  {f.correction_steps && (
                    <div className="bg-blue-50 rounded-lg p-3 text-xs text-blue-800">
                      <strong>Corrección:</strong> {f.correction_steps}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function CitationsTab({ advId }: { advId: number }) {
  const { data, isLoading } = useQuery({ queryKey: ['citations', advId], queryFn: () => getCitations(advId) })
  if (isLoading) return <LoadingSpinner />
  if (!data?.length) return <Card><CardContent className="py-10 text-center text-slate-400">Sin citas registradas</CardContent></Card>

  return (
    <Card>
      <CardContent className="p-0">
        {data.map((c, i) => (
          <div key={c.id} className={`px-5 py-3 ${i < data.length - 1 ? 'border-b border-slate-100' : ''}`}>
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm text-slate-700 flex-1">{c.raw_reference}</p>
              <Badge variant={c.status === 'Con DOI' ? 'success' : c.status === 'No encontrada' ? 'error' : 'gray'}>
                {c.status}
              </Badge>
            </div>
            {c.doi && <p className="text-xs text-blue-600 mt-1">DOI: {c.doi}</p>}
            {c.suggestion && <p className="text-xs text-amber-700 mt-1">Sugerencia: {c.suggestion}</p>}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

function SimilarityTab({ advId }: { advId: number }) {
  const { data, isLoading } = useQuery({ queryKey: ['similarity', advId], queryFn: () => getSimilarity(advId) })
  if (isLoading) return <LoadingSpinner />
  if (!data?.length) return <Card><CardContent className="py-10 text-center text-slate-400">Sin resultados de similitud</CardContent></Card>

  return (
    <Card>
      <CardContent className="p-0">
        {data.map((r, i) => (
          <div key={r.id} className={`px-5 py-3 ${i < data.length - 1 ? 'border-b border-slate-100' : ''}`}>
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-slate-800">{r.compared_title ?? 'Avance desconocido'}</p>
                {r.section_ref && <p className="text-xs text-slate-400 mt-0.5">Sección: {r.section_ref}</p>}
              </div>
              <div className="text-right shrink-0">
                <span className={`text-lg font-bold ${r.similarity >= 0.3 ? 'text-red-600' : r.similarity >= 0.15 ? 'text-amber-600' : 'text-emerald-600'}`}>
                  {(r.similarity * 100).toFixed(1)}%
                </span>
                <p className="text-xs text-slate-400">{r.status}</p>
              </div>
            </div>
            <Progress value={r.similarity * 100} className="mt-2" color={r.similarity >= 0.3 ? 'bg-red-500' : r.similarity >= 0.15 ? 'bg-amber-500' : 'bg-emerald-500'} />
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
