import { useState, useRef, useCallback } from 'react'
import {
  Bot, Upload, Loader2, AlertTriangle, CheckCircle2, ChevronDown,
  ChevronUp, Info, FileText, ShieldAlert, BarChart3, Download,
} from 'lucide-react'
import { checkAIContent, downloadAIDetectionReport } from '../api'
import type { AIDetectionReport, AIParagraph } from '../api'

// ── Risk config ───────────────────────────────────────────────────────────────
const RISK: Record<string, { bg: string; text: string; border: string; label: string; ring: string }> = {
  Bajo:      { bg: 'bg-green-50',  text: 'text-green-700',  border: 'border-green-300',  label: 'Riesgo Bajo',      ring: '#22c55e' },
  Moderado:  { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-300', label: 'Riesgo Moderado',  ring: '#eab308' },
  Alto:      { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-300', label: 'Riesgo Alto',      ring: '#f97316' },
  'Muy alto':{ bg: 'bg-red-50',    text: 'text-red-700',    border: 'border-red-300',    label: 'Riesgo Muy Alto',  ring: '#ef4444' },
}

// ── Score ring ────────────────────────────────────────────────────────────────
function ScoreRing({ pct, label }: { pct: number; label: string }) {
  const cfg  = RISK[label] ?? RISK['Moderado']
  const r    = 52
  const circ = 2 * Math.PI * r
  const dash = circ * (1 - pct / 100)
  return (
    <svg width="148" height="148" viewBox="0 0 148 148">
      <circle cx="74" cy="74" r={r} fill="none" stroke="#e5e7eb" strokeWidth="13" />
      <circle cx="74" cy="74" r={r} fill="none" stroke={cfg.ring} strokeWidth="13"
        strokeDasharray={circ} strokeDashoffset={dash}
        strokeLinecap="round" transform="rotate(-90 74 74)"
        style={{ transition: 'stroke-dashoffset 1.2s ease' }} />
      <text x="74" y="66" textAnchor="middle" fontSize="28" fontWeight="bold" fill={cfg.ring}>
        {pct.toFixed(1)}%
      </text>
      <text x="74" y="86" textAnchor="middle" fontSize="11" fill="#6b7280">prob. IA</text>
    </svg>
  )
}

// ── Metric bar ────────────────────────────────────────────────────────────────
interface MetricCardProps {
  name: string
  value: string
  aiProb: number   // 0-1: how AI-like is this metric
  hint: string
}
function MetricCard({ name, value, aiProb, hint }: MetricCardProps) {
  const color = aiProb < 0.35 ? 'bg-green-500' : aiProb < 0.65 ? 'bg-yellow-500' : 'bg-red-500'
  const label = aiProb < 0.35 ? 'text-green-700' : aiProb < 0.65 ? 'text-yellow-700' : 'text-red-700'
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{name}</span>
        <span className={`text-xs font-bold ${label}`}>{value}</span>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-2 mb-2">
        <div className={`${color} h-2 rounded-full transition-all duration-700`}
          style={{ width: `${Math.round(aiProb * 100)}%` }} />
      </div>
      <p className="text-xs text-gray-500 leading-tight">{hint}</p>
    </div>
  )
}

// ── Paragraph card ────────────────────────────────────────────────────────────
function ParaCard({ para, rank }: { para: AIParagraph; rank: number }) {
  const [open, setOpen] = useState(false)
  const sc     = para.score
  const bar    = sc < 40 ? 'bg-yellow-400' : sc < 65 ? 'bg-orange-500' : 'bg-red-500'
  const badge  = sc < 40 ? 'bg-yellow-100 text-yellow-800' : sc < 65 ? 'bg-orange-100 text-orange-800' : 'bg-red-100 text-red-800'
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="p-4 cursor-pointer hover:bg-gray-50 flex items-start gap-3"
        onClick={() => setOpen(o => !o)}>
        <span className="shrink-0 w-6 h-6 rounded-full bg-gray-100 text-gray-500 text-xs font-bold flex items-center justify-center mt-0.5">
          {rank}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${badge}`}>
              {sc.toFixed(1)}% IA
            </span>
          </div>
          <p className="text-sm text-gray-700 leading-snug line-clamp-2">{para.text}</p>
          <div className="mt-2 w-full bg-gray-100 rounded-full h-1.5">
            <div className={`${bar} h-1.5 rounded-full`} style={{ width: `${sc}%` }} />
          </div>
        </div>
        <button className="shrink-0 text-gray-400 mt-1">
          {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>
      {open && (
        <div className="border-t border-gray-100 bg-gray-50 p-4 space-y-3">
          <p className="text-sm text-gray-700 leading-relaxed">{para.text}</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {[
              { k: 'Uniformidad oracional', v: para.metrics.sentence_cv.toFixed(3) },
              { k: 'Diversidad léxica (TTR)', v: para.metrics.ttr.toFixed(3) },
              { k: 'Repetición n-gramas', v: (para.metrics.ngram_repetition * 100).toFixed(2) + '%' },
              { k: 'Entropía bigrama', v: para.metrics.bigram_entropy.toFixed(3) },
              { k: 'Transiciones formales', v: (para.metrics.formal_words * 100).toFixed(2) + '%' },
              { k: 'Long. prom. oración', v: para.metrics.avg_sentence_len.toFixed(1) + ' pal.' },
            ].map(({ k, v }) => (
              <div key={k} className="bg-white border border-gray-100 rounded-lg p-2">
                <p className="text-[10px] text-gray-400 leading-tight">{k}</p>
                <p className="text-sm font-semibold text-gray-700">{v}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function DetectorIAPage() {
  const [dragging,    setDragging]    = useState(false)
  const [loading,     setLoading]     = useState(false)
  const [report,      setReport]      = useState<AIDetectionReport | null>(null)
  const [error,       setError]       = useState<string | null>(null)
  const [fileName,    setFileName]    = useState('')
  const [downloading, setDownloading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const analyze = useCallback(async (file: File) => {
    if (!['pdf', 'docx', 'txt'].includes(file.name.split('.').pop()?.toLowerCase() ?? '')) {
      setError('Formato no admitido. Sube un archivo PDF, DOCX o TXT.')
      return
    }
    setError(null)
    setReport(null)
    setFileName(file.name)
    setLoading(true)
    try {
      const r = await checkAIContent(file)
      setReport(r)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? 'Error analizando el documento.')
    } finally {
      setLoading(false)
    }
  }, [])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) analyze(file)
  }, [analyze])

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) analyze(file)
    e.target.value = ''
  }

  const handleDownload = async () => {
    if (!report) return
    setDownloading(true)
    try { await downloadAIDetectionReport(report) }
    catch { setError('Error generando el reporte PDF.') }
    finally { setDownloading(false) }
  }

  const cfg = report ? (RISK[report.risk_level] ?? RISK['Moderado']) : null

  return (
    <div className="max-w-4xl mx-auto space-y-6">

      {/* Header */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2.5 bg-violet-100 rounded-xl">
            <Bot size={22} className="text-violet-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Detector de Contenido IA</h1>
            <p className="text-sm text-gray-500">Estimación probabilística — no constituye prueba definitiva</p>
          </div>
        </div>
        <p className="text-sm text-gray-600 mt-3 leading-relaxed">
          Analiza indicadores lingüísticos estadísticos (uniformidad oracional, diversidad léxica,
          entropía, repetición de frases, transiciones formales) para estimar la probabilidad de
          que el texto haya sido generado por IA. Compatible con PDF, DOCX y TXT.
        </p>
      </div>

      {/* Upload zone */}
      <div
        className={`relative border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all duration-200 ${
          dragging ? 'border-violet-400 bg-violet-50' : 'border-gray-300 hover:border-violet-400 hover:bg-gray-50'
        }`}
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input ref={inputRef} type="file" accept=".pdf,.docx,.txt" className="hidden" onChange={onFile} />
        <Upload size={36} className="mx-auto mb-3 text-gray-400" />
        <p className="text-base font-semibold text-gray-700">
          {dragging ? 'Suelta el archivo aquí' : 'Arrastra tu documento o haz clic para seleccionar'}
        </p>
        <p className="text-sm text-gray-400 mt-1">PDF, DOCX o TXT — máx. 20 MB</p>
      </div>

      {/* Loading */}
      {loading && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 text-center">
          <Loader2 size={40} className="animate-spin mx-auto mb-3 text-violet-500" />
          <p className="text-base font-semibold text-gray-700">Analizando <span className="text-violet-600">{fileName}</span>…</p>
          <p className="text-sm text-gray-400 mt-1">
            El análisis estadístico tarda ~3 s. Si el modelo de HuggingFace está cargando por primera vez, puede demorar 1-2 min.
          </p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-5 flex items-start gap-3">
          <AlertTriangle size={20} className="text-red-500 shrink-0 mt-0.5" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Results */}
      {report && !loading && cfg && (
        <div className="space-y-5">

          {/* Summary card */}
          <div className={`bg-white rounded-2xl shadow-sm border-2 ${cfg.border} p-6`}>
            <div className="flex flex-col sm:flex-row gap-6 items-center sm:items-start">
              <ScoreRing pct={report.ai_probability} label={report.risk_level} />
              <div className="flex-1 space-y-3">
                <div className="flex items-center gap-2 flex-wrap justify-between">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`px-3 py-1 rounded-full text-sm font-bold border ${cfg.bg} ${cfg.text} ${cfg.border}`}>
                    {cfg.label}
                  </span>
                  {report.low_confidence && (
                    <span className="px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-600 border border-gray-200">
                      Confianza baja (texto corto)
                    </span>
                  )}
                  {report.hf_model_used && (
                    <span className="px-2 py-0.5 rounded-full text-xs bg-violet-100 text-violet-700 border border-violet-200">
                      + Modelo HuggingFace
                    </span>
                  )}
                </div>
                  <button
                    onClick={handleDownload}
                    disabled={downloading}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-violet-600 hover:bg-violet-700 disabled:bg-gray-300 text-white text-sm font-semibold rounded-lg transition-colors shrink-0"
                  >
                    {downloading
                      ? <><Loader2 size={14} className="animate-spin" /> Generando…</>
                      : <><Download size={14} /> Descargar PDF</>
                    }
                  </button>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-center">
                  {[
                    { label: 'Palabras', value: report.total_words.toLocaleString() },
                    { label: 'Oraciones', value: report.total_sentences.toLocaleString() },
                    { label: 'Párrafos', value: report.total_paragraphs.toLocaleString() },
                    { label: 'Sospechosos', value: report.suspicious_count.toString() },
                    { label: 'Score estadístico', value: `${report.statistical_score}%` },
                    { label: 'Score HF', value: report.hf_score !== null ? `${report.hf_score}%` : 'N/D' },
                  ].map(({ label, value }) => (
                    <div key={label} className="bg-gray-50 rounded-xl p-2.5">
                      <p className="text-[11px] text-gray-400 uppercase tracking-wide">{label}</p>
                      <p className="text-base font-bold text-gray-800">{value}</p>
                    </div>
                  ))}
                </div>
                <div className="flex items-center gap-2">
                  <FileText size={13} className="text-gray-400 shrink-0" />
                  <span className="text-xs text-gray-400 truncate">{report.filename} — {report.analyzed_at} ({report.elapsed_s}s)</span>
                </div>
              </div>
            </div>
          </div>

          {/* Metrics grid */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 size={18} className="text-violet-600" />
              <h2 className="text-base font-bold text-gray-800">Métricas Lingüísticas</h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {(() => {
                const m = report.global_metrics
                const clamp = (v: number) => Math.max(0, Math.min(1, v))
                const cvProb    = clamp((0.60 - m.sentence_cv)   / 0.52)
                const ttrProb   = clamp((0.72 - m.type_token_ratio) / 0.28)
                const repProb   = clamp((m.ngram_repetition - 0.01) / 0.09)
                const entProb   = clamp((3.5 - m.bigram_entropy)  / 2.5)
                const frmProb   = clamp((m.formal_word_ratio - 0.01) / 0.07)
                const lenProb   = clamp((m.avg_sentence_len - 14.0) / 16.0)
                return [
                  {
                    name: 'Uniformidad oracional',
                    value: m.sentence_cv.toFixed(3),
                    aiProb: cvProb,
                    hint: m.sentence_cv < 0.30
                      ? `${m.sentence_cv.toFixed(3)} — Oraciones muy uniformes (indicador IA)`
                      : `${m.sentence_cv.toFixed(3)} — Variación natural de longitud`,
                  },
                  {
                    name: 'Diversidad léxica (TTR)',
                    value: m.type_token_ratio.toFixed(3),
                    aiProb: ttrProb,
                    hint: m.type_token_ratio < 0.55
                      ? `${m.type_token_ratio.toFixed(3)} — Vocabulario limitado (indicador IA)`
                      : `${m.type_token_ratio.toFixed(3)} — Vocabulario variado`,
                  },
                  {
                    name: 'Repetición de frases',
                    value: (m.ngram_repetition * 100).toFixed(2) + '%',
                    aiProb: repProb,
                    hint: m.ngram_repetition > 0.06
                      ? `${(m.ngram_repetition * 100).toFixed(2)}% — Frases repetidas frecuentes (indicador IA)`
                      : `${(m.ngram_repetition * 100).toFixed(2)}% — Repetición baja`,
                  },
                  {
                    name: 'Predictibilidad (entropía)',
                    value: m.bigram_entropy.toFixed(3),
                    aiProb: entProb,
                    hint: m.bigram_entropy < 2.0
                      ? `${m.bigram_entropy.toFixed(3)} — Texto predecible (indicador IA)`
                      : `${m.bigram_entropy.toFixed(3)} — Entropía normal`,
                  },
                  {
                    name: 'Transiciones formales',
                    value: (m.formal_word_ratio * 100).toFixed(2) + '%',
                    aiProb: frmProb,
                    hint: m.formal_word_ratio > 0.045
                      ? `${(m.formal_word_ratio * 100).toFixed(2)}% — Uso excesivo de conectores formales`
                      : `${(m.formal_word_ratio * 100).toFixed(2)}% — Conectores en rango normal`,
                  },
                  {
                    name: 'Long. prom. oración',
                    value: m.avg_sentence_len.toFixed(1) + ' pal.',
                    aiProb: lenProb,
                    hint: m.avg_sentence_len > 26
                      ? `${m.avg_sentence_len.toFixed(1)} pal. — Oraciones largas (indicador IA)`
                      : `${m.avg_sentence_len.toFixed(1)} pal. — Longitud normal`,
                  },
                ].map(props => <MetricCard key={props.name} {...props} />)
              })()}
            </div>
          </div>

          {/* Suspicious paragraphs */}
          {report.suspicious_paragraphs.length > 0 && (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
              <div className="flex items-center gap-2 mb-4">
                <ShieldAlert size={18} className="text-orange-500" />
                <h2 className="text-base font-bold text-gray-800">
                  Párrafos Sospechosos ({report.suspicious_paragraphs.length})
                </h2>
                <span className="text-xs text-gray-400">Puntuación ≥ 50% de probabilidad IA</span>
              </div>
              <div className="space-y-3">
                {report.suspicious_paragraphs.map((p, i) => (
                  <ParaCard key={i} para={p} rank={i + 1} />
                ))}
              </div>
            </div>
          )}

          {report.suspicious_paragraphs.length === 0 && (
            <div className="bg-green-50 border border-green-200 rounded-2xl p-5 flex items-start gap-3">
              <CheckCircle2 size={20} className="text-green-600 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-green-800">Sin párrafos altamente sospechosos</p>
                <p className="text-sm text-green-700 mt-0.5">Ningún párrafo superó el umbral del 50% de probabilidad de IA de forma individual.</p>
              </div>
            </div>
          )}

          {/* Methods */}
          <div className="bg-gray-50 border border-gray-200 rounded-2xl p-4 flex items-center gap-2 flex-wrap">
            <Info size={15} className="text-gray-400 shrink-0" />
            <span className="text-xs text-gray-500">
              Métodos usados:{' '}
              <strong>{report.methods_used.includes('hf_model') ? 'Análisis estadístico + Modelo HuggingFace (Hello-SimpleAI/chatgpt-detector-roberta)' : 'Análisis estadístico lingüístico'}</strong>
              {!report.methods_used.includes('hf_model') && (
                <span className="ml-1 text-gray-400">— instala <code className="bg-white px-1 rounded text-xs">transformers</code> para activar el modelo de HuggingFace</span>
              )}
            </span>
          </div>

          {/* Disclaimer */}
          <div className="bg-amber-50 border-2 border-amber-300 rounded-2xl p-5">
            <div className="flex items-start gap-3">
              <AlertTriangle size={20} className="text-amber-600 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-bold text-amber-800 mb-2">AVISO IMPORTANTE</p>
                <p className="text-sm text-amber-800 leading-relaxed">{report.disclaimer}</p>
                <ul className="mt-3 space-y-1">
                  {report.limitations.map((lim, i) => (
                    <li key={i} className="text-xs text-amber-700 flex items-start gap-1.5">
                      <span className="mt-0.5 shrink-0">•</span>
                      {lim}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

        </div>
      )}

    </div>
  )
}
