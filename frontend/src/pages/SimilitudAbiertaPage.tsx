import { useState, useRef } from 'react'
import {
  ShieldCheck, Upload, Loader2, AlertTriangle, CheckCircle2,
  ExternalLink, ChevronDown, ChevronUp, Info, FileText, Search, Download,
} from 'lucide-react'
import { checkSimilarity, downloadSimilarityReport } from '../api'
import type { SimilarityReport, SimilaritySource } from '../api'

// ── Helpers ───────────────────────────────────────────────────────────────────
const RISK_CONFIG: Record<string, { bg: string; text: string; border: string; label: string }> = {
  Bajo:      { bg: 'bg-green-50',  text: 'text-green-700',  border: 'border-green-300', label: 'Riesgo Bajo' },
  Moderado:  { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-300',label: 'Riesgo Moderado' },
  Alto:      { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-300',label: 'Riesgo Alto' },
  'Muy alto':{ bg: 'bg-red-50',    text: 'text-red-700',    border: 'border-red-300',   label: 'Riesgo Muy Alto' },
}

const API_COLORS: Record<string, string> = {
  OpenAlex: 'bg-blue-100 text-blue-700',
  Crossref: 'bg-purple-100 text-purple-700',
  arXiv:    'bg-orange-100 text-orange-700',
  CORE:     'bg-green-100 text-green-700',
  Interno:  'bg-gray-100 text-gray-700',
}

function ScoreRing({ pct }: { pct: number }) {
  const color = pct < 10 ? '#22c55e' : pct < 20 ? '#eab308' : pct < 35 ? '#f97316' : '#ef4444'
  const r = 52, circ = 2 * Math.PI * r
  const dash = circ * (1 - pct / 100)
  return (
    <svg width="140" height="140" viewBox="0 0 140 140">
      <circle cx="70" cy="70" r={r} fill="none" stroke="#e5e7eb" strokeWidth="12" />
      <circle cx="70" cy="70" r={r} fill="none" stroke={color} strokeWidth="12"
        strokeDasharray={circ} strokeDashoffset={dash}
        strokeLinecap="round" transform="rotate(-90 70 70)"
        style={{ transition: 'stroke-dashoffset 1s ease' }} />
      <text x="70" y="62" textAnchor="middle" fontSize="26" fontWeight="bold" fill={color}>{pct.toFixed(1)}%</text>
      <text x="70" y="84" textAnchor="middle" fontSize="11" fill="#6b7280">similitud</text>
    </svg>
  )
}

function SourceCard({ src }: { src: SimilaritySource }) {
  const [expanded, setExpanded] = useState(false)
  const sim = src.similarity_score
  const barColor = sim < 10 ? 'bg-green-500' : sim < 20 ? 'bg-yellow-500' : sim < 35 ? 'bg-orange-500' : 'bg-red-500'
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div
        className="p-4 cursor-pointer hover:bg-gray-50 flex items-start gap-3"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${API_COLORS[src.api] || 'bg-gray-100 text-gray-600'}`}>
              {src.api}
            </span>
            {src.year && <span className="text-xs text-gray-400">{src.year}</span>}
            {src.doi && (
              <a href={src.url || `https://doi.org/${src.doi}`} target="_blank" rel="noreferrer"
                onClick={e => e.stopPropagation()}
                className="text-xs text-blue-600 hover:underline flex items-center gap-0.5">
                DOI <ExternalLink size={10} />
              </a>
            )}
            {!src.doi && src.url && (
              <a href={src.url} target="_blank" rel="noreferrer"
                onClick={e => e.stopPropagation()}
                className="text-xs text-blue-600 hover:underline flex items-center gap-0.5">
                Enlace <ExternalLink size={10} />
              </a>
            )}
          </div>
          <p className="text-sm font-medium text-gray-800 leading-tight line-clamp-2">
            {src.title || '(Sin título)'}
          </p>
          {src.authors?.length > 0 && (
            <p className="text-xs text-gray-500 mt-0.5">
              {src.authors.filter(Boolean).join(', ')}
              {src.source_name ? ` — ${src.source_name}` : ''}
            </p>
          )}
          {/* Barra de similitud */}
          <div className="mt-2 flex items-center gap-2">
            <div className="flex-1 bg-gray-100 rounded-full h-1.5">
              <div className={`h-1.5 rounded-full ${barColor}`} style={{ width: `${Math.min(sim, 100)}%` }} />
            </div>
            <span className={`text-xs font-bold ${sim < 10 ? 'text-green-600' : sim < 20 ? 'text-yellow-600' : sim < 35 ? 'text-orange-600' : 'text-red-600'}`}>
              {sim}%
            </span>
          </div>
        </div>
        <div className="shrink-0 text-gray-400 mt-1">
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </div>

      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-100 pt-3 space-y-3">
          {src.abstract && (
            <div>
              <p className="text-xs font-semibold text-gray-500 mb-1">Resumen / Abstract</p>
              <p className="text-xs text-gray-600 leading-relaxed line-clamp-4">{src.abstract}</p>
            </div>
          )}
          {src.matching_fragments?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 mb-2">
                Fragmentos similares detectados ({src.matching_fragments.length})
              </p>
              <div className="space-y-2">
                {src.matching_fragments.map((frag, i) => (
                  <div key={i} className="bg-yellow-50 border border-yellow-200 rounded-md p-3">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-semibold text-yellow-700">Fragmento {i + 1}</span>
                      <span className="text-xs bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded font-medium">
                        {frag.similarity}% overlap
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <p className="text-xs font-medium text-gray-500 mb-0.5">Tu documento:</p>
                        <p className="text-xs text-gray-700 italic">"{frag.doc_fragment}"</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-gray-500 mb-0.5">Fuente:</p>
                        <p className="text-xs text-gray-700 italic">"{frag.source_fragment}"</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Página principal ──────────────────────────────────────────────────────────
export default function SimilitudAbiertaPage() {
  const [file, setFile]             = useState<File | null>(null)
  const [dragging, setDragging]     = useState(false)
  const [loading, setLoading]       = useState(false)
  const [report, setReport]         = useState<SimilarityReport | null>(null)
  const [error, setError]           = useState('')
  const [downloading, setDownloading] = useState(false)
  const inputRef                    = useRef<HTMLInputElement>(null)

  const handleFile = (f: File | null) => {
    if (!f) return
    const ext = f.name.split('.').pop()?.toLowerCase() || ''
    if (!['pdf','docx','txt'].includes(ext)) {
      setError('Solo se aceptan archivos PDF, DOCX o TXT.')
      return
    }
    setFile(f); setError(''); setReport(null)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragging(false)
    handleFile(e.dataTransfer.files[0] || null)
  }

  const handleAnalyze = async () => {
    if (!file) return
    setLoading(true); setError(''); setReport(null)
    try {
      const result = await checkSimilarity(file)
      setReport(result)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Error al analizar el documento'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadReport = async () => {
    if (!report) return
    setDownloading(true)
    try {
      await downloadSimilarityReport(report)
    } catch {
      setError('Error generando el reporte PDF. Intenta de nuevo.')
    } finally {
      setDownloading(false)
    }
  }

  const risk = report ? (RISK_CONFIG[report.risk_level] || RISK_CONFIG['Bajo']) : null

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-blue-100 rounded-lg">
          <ShieldCheck className="text-blue-700" size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Similitud Académica Abierta</h1>
          <p className="text-sm text-gray-500">
            Comparación gratuita contra OpenAlex, Crossref, arXiv y documentos internos
          </p>
        </div>
      </div>

      {/* Aviso importante */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 flex gap-3">
        <Info size={18} className="text-blue-500 shrink-0 mt-0.5" />
        <p className="text-sm text-blue-800">
          <strong>Alcance limitado:</strong> Este sistema compara exclusivamente contra repositorios
          de acceso abierto y documentos internos. No accede a bases privadas como Scopus, Turnitin
          o revistas cerradas. Un resultado bajo <em>no garantiza</em> originalidad absoluta.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Panel izquierdo: carga y control */}
        <div className="space-y-4">

          {/* Zona de carga */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 space-y-4">
            <h2 className="font-semibold text-gray-800 flex items-center gap-2">
              <Upload size={16} className="text-blue-600" /> Cargar documento
            </h2>

            <div
              onClick={() => inputRef.current?.click()}
              onDrop={handleDrop}
              onDragOver={e => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                dragging ? 'border-blue-400 bg-blue-50' :
                file      ? 'border-green-400 bg-green-50' :
                            'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
              }`}
            >
              <input ref={inputRef} type="file" accept=".pdf,.docx,.txt" className="hidden"
                onChange={e => handleFile(e.target.files?.[0] || null)} />
              {file ? (
                <div className="space-y-1">
                  <FileText size={32} className="mx-auto text-green-500" />
                  <p className="text-sm font-medium text-green-700">{file.name}</p>
                  <p className="text-xs text-green-500">{(file.size / 1024).toFixed(1)} KB</p>
                </div>
              ) : (
                <div className="space-y-2">
                  <Upload size={32} className="mx-auto text-gray-300" />
                  <p className="text-sm text-gray-500">Arrastra tu archivo aquí o haz clic</p>
                  <p className="text-xs text-gray-400">PDF, DOCX o TXT</p>
                </div>
              )}
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm flex gap-2">
                <AlertTriangle size={16} className="shrink-0 mt-0.5" /> {error}
              </div>
            )}

            <button
              onClick={handleAnalyze}
              disabled={!file || loading}
              className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-lg transition-colors"
            >
              {loading ? (
                <><Loader2 size={18} className="animate-spin" /> Analizando... (30-60 seg)</>
              ) : (
                <><Search size={18} /> Analizar similitud</>
              )}
            </button>
          </div>

          {/* Fuentes consultadas */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
            <h2 className="font-semibold text-gray-800 mb-3">Fuentes consultadas</h2>
            <div className="space-y-2 text-sm">
              {[
                ['OpenAlex', 'bg-blue-100 text-blue-700', '200M+ publicaciones académicas abiertas'],
                ['Crossref', 'bg-purple-100 text-purple-700', 'Metadatos de 150M+ artículos con DOI'],
                ['arXiv', 'bg-orange-100 text-orange-700', 'Preprints de física, CS, matemáticas'],
                ['CORE', 'bg-green-100 text-green-700', 'Repositorios abiertos (requiere clave)'],
                ['Interno', 'bg-gray-100 text-gray-700', 'Documentos subidos al sistema'],
              ].map(([name, cls, desc]) => (
                <div key={name} className="flex items-start gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 mt-0.5 ${cls}`}>{name}</span>
                  <span className="text-gray-500 text-xs">{desc}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Panel derecho: resultados */}
        <div className="space-y-4">
          {loading && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-10 flex flex-col items-center gap-4">
              <Loader2 size={40} className="text-blue-500 animate-spin" />
              <div className="text-center">
                <p className="font-semibold text-gray-700">Analizando documento...</p>
                <p className="text-sm text-gray-400 mt-1">Consultando OpenAlex, Crossref, arXiv y documentos internos</p>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                <div className="h-1.5 bg-blue-500 rounded-full animate-pulse w-2/3" />
              </div>
            </div>
          )}

          {report && !loading && (
            <>
              {/* Tarjeta principal de resultado */}
              <div className={`rounded-xl border-2 ${risk!.border} ${risk!.bg} p-5`}>
                <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
                  <div>
                    <h2 className="font-bold text-gray-800 text-lg">Resultado del análisis</h2>
                    <p className="text-xs text-gray-500 mt-0.5">{report.filename}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-3 py-1 rounded-full text-sm font-bold ${risk!.text} border ${risk!.border}`}>
                      {risk!.label}
                    </span>
                    <button
                      onClick={handleDownloadReport}
                      disabled={downloading}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white text-sm font-semibold rounded-lg transition-colors"
                    >
                      {downloading
                        ? <><Loader2 size={14} className="animate-spin" /> Generando…</>
                        : <><Download size={14} /> Descargar PDF</>
                      }
                    </button>
                  </div>
                </div>

                <div className="flex items-center gap-6">
                  <ScoreRing pct={report.overall_similarity} />
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2">
                      <Search size={14} className="text-gray-400" />
                      <span className="text-gray-600">
                        <strong>{report.total_sources_checked}</strong> fuentes consultadas
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <AlertTriangle size={14} className="text-gray-400" />
                      <span className="text-gray-600">
                        <strong>{report.matching_sources}</strong> fuentes con coincidencias
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {report.apis_consulted.map(api => (
                        <span key={api} className={`text-xs px-1.5 py-0.5 rounded font-medium ${API_COLORS[api] || 'bg-gray-100 text-gray-600'}`}>
                          {api}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Metadatos detectados */}
              {report.document_metadata?.title && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                  <p className="text-xs font-semibold text-gray-500 mb-1">Título detectado</p>
                  <p className="text-sm text-gray-800">{report.document_metadata.title}</p>
                  {report.document_metadata.keywords?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {report.document_metadata.keywords.map(k => (
                        <span key={k} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{k}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Fuentes coincidentes */}
              {report.sources.length > 0 && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
                  <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                    <CheckCircle2 size={16} className="text-blue-500" />
                    Fuentes con mayor coincidencia ({report.sources.length})
                  </h3>
                  <div className="space-y-2">
                    {report.sources.map((src, i) => (
                      <SourceCard key={i} src={src} />
                    ))}
                  </div>
                </div>
              )}

              {report.sources.length === 0 && (
                <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center">
                  <CheckCircle2 size={32} className="mx-auto text-green-500 mb-2" />
                  <p className="font-semibold text-green-700">Sin coincidencias significativas</p>
                  <p className="text-sm text-green-600 mt-1">
                    No se encontraron fuentes abiertas con similitud relevante.
                  </p>
                </div>
              )}

              {/* Limitaciones */}
              <div className="bg-gray-50 rounded-xl border border-gray-200 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Info size={14} className="text-gray-400" />
                  <p className="text-xs font-semibold text-gray-500">LIMITACIONES DEL ANÁLISIS</p>
                </div>
                <ul className="space-y-1">
                  {report.limitations.map((l, i) => (
                    <li key={i} className="text-xs text-gray-500 flex gap-1.5">
                      <span className="shrink-0 mt-0.5">•</span>
                      <span>{l}</span>
                    </li>
                  ))}
                </ul>
                <p className="text-xs text-gray-400 mt-2">
                  Análisis realizado: {new Date(report.analyzed_at).toLocaleString('es-PE')}
                </p>
              </div>
            </>
          )}

          {!report && !loading && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-10 flex flex-col items-center text-center text-gray-400 space-y-3">
              <ShieldCheck size={48} className="text-gray-200" />
              <div>
                <p className="font-medium text-gray-500">Sube un documento para analizarlo</p>
                <p className="text-sm mt-1">Los resultados aparecerán aquí.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
