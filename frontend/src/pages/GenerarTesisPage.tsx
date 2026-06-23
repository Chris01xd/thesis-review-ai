import { useState, useRef, useEffect } from 'react'
import {
  FileText, Download, Loader2, Sparkles, BookOpen,
  User, Users, MapPin, Calendar, ImagePlus, X,
  FileUp, GraduationCap, Newspaper, ClipboardList, Link,
  BarChart2, Table2, Image,
} from 'lucide-react'
import { generateDocument, downloadThesisFile, getThesisPdfBlob, getUsers } from '../api'
import type { ThesisResult, DocType } from '../api'

const RESEARCH_LINES = [
  'Gestión de Gobierno y Servicios de TIC',
  'Gestión de Proyectos de TIC',
  'Gestión de Desarrollo de Software',
  'Gestión de Infraestructura y Comunicaciones',
  'Gestión de la Seguridad de la Información',
]

const CITIES = ['Trujillo', 'Guadalupe', 'Lima', 'Arequipa', 'Chiclayo', 'Piura', 'Cusco', 'Iquitos', 'Huancayo']

const DOC_TYPES: { value: DocType; label: string; desc: string; icon: typeof BookOpen; color: string; sections: string[] }[] = [
  {
    value: 'tesis',
    label: 'Tesis',
    desc: 'Documento completo con 5 capítulos, resultados, discusión y conclusiones.',
    icon: GraduationCap,
    color: 'blue',
    sections: [
      'Carátula + Jurado', 'Resumen / Abstract',
      'Cap. I: Introducción', 'Cap. II: Metodología',
      'Cap. III: Resultados', 'Cap. IV: Discusión',
      'Cap. V: Conclusiones', '≤ 25 refs APA V7',
      'Árbol de problemas', 'Declaración jurada',
    ],
  },
  {
    value: 'proyecto_tesis',
    label: 'Proyecto de Tesis',
    desc: 'Propuesta de investigación con cronograma, presupuesto y matrices.',
    icon: ClipboardList,
    color: 'emerald',
    sections: [
      'Carátula', 'Resumen / Abstract',
      'Cap. I: Problema de investigación', 'Cap. II: Marco metodológico',
      'Cap. III: Aspectos administrativos', 'Cronograma de actividades',
      'Presupuesto detallado', 'Matriz de consistencia',
      'Operacionalización de variables', 'Declaración jurada',
    ],
  },
  {
    value: 'articulo',
    label: 'Artículo de Investigación',
    desc: 'Formato de artículo científico con abstract, métodos y resultados.',
    icon: Newspaper,
    color: 'violet',
    sections: [
      'Título + Autores + Filiación', 'Resumen / Abstract + Keywords',
      'I. Introducción', 'II. Materiales y Métodos',
      'III. Resultados', 'IV. Discusión',
      'V. Conclusiones', '≤ 20 referencias',
    ],
  },
]

interface FormState {
  title: string
  authors: string
  advisor: string
  research_line: string
  city: string
  year: number
}

const INITIAL: FormState = {
  title: '',
  authors: '',
  advisor: '',
  research_line: RESEARCH_LINES[0],
  city: 'Trujillo',
  year: new Date().getFullYear(),
}

function parseAuthors(raw: string): string[] {
  return raw.split(/[,;\n]+/).map(a => a.trim()).filter(Boolean)
}

const ORCID_RE = /^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$/

const WORD_NUMS: Record<string, number> = {
  una:1,un:1,dos:2,tres:3,cuatro:4,cinco:5,seis:6,siete:7,ocho:8,nueve:9,diez:10,
}
function parseElementCount(text: string, keywords: string[]): number {
  const kw = keywords.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')
  const m = text.toLowerCase().match(
    new RegExp(`(\\d+|${Object.keys(WORD_NUMS).join('|')})\\s+(?:${kw})`, 'i')
  )
  if (!m) return 0
  return WORD_NUMS[m[1].toLowerCase()] ?? parseInt(m[1]) ?? 0
}
interface ElementsSummary { tables: number; charts: number; images: number }
function parseElementsSummary(text: string): ElementsSummary | null {
  if (!text.trim()) return null
  const t = parseElementCount(text, ['tabla','tablas','cuadro','cuadros'])
  const c = parseElementCount(text, ['gráfico','grafico','gráficos','graficos','diagrama','diagramas','figura','figuras'])
  const i = parseElementCount(text, ['imagen','imágenes','imagenes','foto','fotos','ilustración','ilustraciones'])
  if (!t && !c && !i) return null
  return { tables: t, charts: c, images: i }
}

const colorMap: Record<string, string> = {
  blue:    'border-blue-500 bg-blue-50 text-blue-700',
  emerald: 'border-emerald-500 bg-emerald-50 text-emerald-700',
  violet:  'border-violet-500 bg-violet-50 text-violet-700',
}
const btnColorMap: Record<string, string> = {
  blue:    'bg-blue-600 hover:bg-blue-700',
  emerald: 'bg-emerald-600 hover:bg-emerald-700',
  violet:  'bg-violet-600 hover:bg-violet-700',
}

export default function GenerarTesisPage() {
  const [docType, setDocType]       = useState<DocType>('tesis')
  const [form, setForm]             = useState<FormState>(INITIAL)
  const [authorsOrcid, setAuthorsOrcid] = useState<string[]>([])
  const [loading, setLoading]       = useState(false)
  const [result, setResult]         = useState<ThesisResult | null>(null)
  const [error, setError]           = useState('')
  const [pdfUrl, setPdfUrl]         = useState('')
  const [loadingPdf, setLoadingPdf] = useState(false)
  const [logoData, setLogoData]     = useState<string>('')
  const [logoPreview, setLogoPreview] = useState<string>('')
  const [templateFiles, setTemplateFiles] = useState<File[]>([])
  const [tableInstructions, setTableInstructions] = useState('')
  const [elementsSummary, setElementsSummary] = useState<ElementsSummary | null>(null)
  const [advisors, setAdvisors]     = useState<{ id: number; name: string }[]>([])
  const logoInputRef     = useRef<HTMLInputElement>(null)
  const templateInputRef = useRef<HTMLInputElement>(null)

  const parsedAuthors = parseAuthors(form.authors)

  const setOrcid = (idx: number, val: string) =>
    setAuthorsOrcid(prev => {
      const next = [...prev]
      next[idx] = val
      return next
    })

  useEffect(() => {
    getUsers('ADVISOR')
      .then(users => setAdvisors(users.map(u => ({ id: u.id, name: u.name }))))
      .catch(() => {})
  }, [])

  useEffect(() => {
    setAuthorsOrcid(prev => prev.slice(0, parseAuthors(form.authors).length))
  }, [form.authors])

  const set = (k: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm(f => ({ ...f, [k]: k === 'year' ? Number(e.target.value) : e.target.value }))

  const handleLogoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      const dataUrl = ev.target?.result as string
      setLogoData(dataUrl)
      setLogoPreview(dataUrl)
    }
    reader.readAsDataURL(file)
  }

  const handleTemplateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? [])
    if (!files.length) return
    setTemplateFiles(prev => {
      const existing = new Set(prev.map(f => f.name))
      const added = files.filter(f => !existing.has(f.name))
      return [...prev, ...added].slice(0, 5)
    })
    if (templateInputRef.current) templateInputRef.current.value = ''
  }

  const removeTemplateFile = (idx: number) =>
    setTemplateFiles(prev => prev.filter((_, i) => i !== idx))

  const removeLogo = () => {
    setLogoData('')
    setLogoPreview('')
    if (logoInputRef.current) logoInputRef.current.value = ''
  }

  const orcidValid = authorsOrcid.every(o => !o?.trim() || ORCID_RE.test(o.trim()))
  const valid = form.title.trim() && form.authors.trim() && form.advisor.trim() && orcidValid
  const activeType = DOC_TYPES.find(d => d.value === docType)!

  const handleGenerate = async () => {
    if (!valid) return
    setLoading(true)
    setError('')
    setResult(null)
    setPdfUrl('')
    try {
      const orcidValues = parsedAuthors.map((_, i) => (authorsOrcid[i] || '').trim())
      const hasOrcid   = orcidValues.some(Boolean)
      const res = await generateDocument({
        doc_type:      docType,
        title:         form.title.trim(),
        authors:       form.authors.trim(),
        advisor:       form.advisor.trim(),
        research_line: form.research_line,
        city:          form.city,
        year:          form.year,
        logo_data:     logoData || undefined,
        authors_orcid:     hasOrcid ? orcidValues.join(',') : undefined,
        template_files:    templateFiles.length ? templateFiles : undefined,
        table_instructions: tableInstructions.trim() || undefined,
      })
      setResult(res)
      setLoadingPdf(true)
      try {
        const url = await getThesisPdfBlob(res.pdf_file)
        setPdfUrl(url)
      } finally {
        setLoadingPdf(false)
      }
    } catch (e: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const detail = (e as any)?.response?.data?.detail
      const msg = detail
        ? String(detail).slice(0, 400)
        : e instanceof Error ? e.message : 'Error al generar el documento'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = (type: 'pdf' | 'docx') => {
    if (!result) return
    downloadThesisFile(type === 'pdf' ? result.pdf_file : result.docx_file)
  }

  const docTypeLabel: Record<DocType, string> = {
    tesis: 'Tesis',
    proyecto_tesis: 'Proyecto de Tesis',
    articulo: 'Artículo de Investigación',
  }

  return (
    <div className="space-y-6 p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-blue-100 rounded-lg">
          <BookOpen className="text-blue-700" size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Generador de Documentos Académicos</h1>
          <p className="text-sm text-gray-500">
            Genera tesis, proyectos de tesis o artículos en PDF y Word a partir de tus datos y una plantilla opcional
          </p>
        </div>
      </div>

      {/* Selector de tipo de documento */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {DOC_TYPES.map(dt => {
          const Icon = dt.icon
          const isActive = docType === dt.value
          return (
            <button
              key={dt.value}
              onClick={() => { setDocType(dt.value); setResult(null); setPdfUrl('') }}
              className={`text-left p-4 rounded-xl border-2 transition-all ${
                isActive
                  ? colorMap[dt.color]
                  : 'border-gray-200 bg-white hover:border-gray-300 text-gray-700'
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <Icon size={18} />
                <span className="font-semibold text-sm">{dt.label}</span>
              </div>
              <p className="text-xs opacity-80">{dt.desc}</p>
            </button>
          )
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ── FORMULARIO ── */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-5">
          <div className="flex items-center gap-2 pb-2 border-b border-gray-100">
            <Sparkles size={18} className="text-blue-600" />
            <h2 className="font-semibold text-gray-800">Datos del documento</h2>
          </div>

          {/* Título */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700 flex items-center gap-1.5">
              <FileText size={14} /> Título de la investigación *
            </label>
            <textarea
              value={form.title}
              onChange={set('title')}
              rows={3}
              placeholder="Ej: Sistema de Gestión de Inventarios basado en Machine Learning para la empresa XYZ S.A.C."
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>

          {/* Autores */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700 flex items-center gap-1.5">
              <Users size={14} /> Autor(es) * <span className="font-normal text-gray-400">(separar con comas)</span>
            </label>
            <input
              type="text"
              value={form.authors}
              onChange={set('authors')}
              placeholder="Ej: Juan Pérez López, María Rodríguez Sánchez"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* ORCID por autor */}
          {parsedAuthors.length > 0 && (
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700 flex items-center gap-1.5">
                <Link size={14} /> ORCID de autor(es)
                <span className="font-normal text-gray-400">(opcional)</span>
              </label>
              {parsedAuthors.map((name, idx) => {
                const val = authorsOrcid[idx] || ''
                const invalid = val && !ORCID_RE.test(val)
                return (
                  <div key={idx} className="space-y-1">
                    <span className="text-xs text-gray-500 font-medium">{name}</span>
                    <input
                      type="text"
                      value={val}
                      onChange={e => setOrcid(idx, e.target.value)}
                      placeholder="0000-0000-0000-0000"
                      maxLength={19}
                      className={`w-full border rounded-lg px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                        invalid
                          ? 'border-red-400 bg-red-50 focus:ring-red-400'
                          : 'border-gray-300'
                      }`}
                    />
                    {invalid && (
                      <p className="text-xs text-red-500">Formato: 0000-0000-0000-0000</p>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {/* Asesor */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700 flex items-center gap-1.5">
              <User size={14} /> Asesor *
            </label>
            {advisors.length > 0 ? (
              <select
                value={form.advisor}
                onChange={set('advisor')}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="">— Selecciona un asesor —</option>
                {advisors.map(a => (
                  <option key={a.id} value={a.name}>{a.name}</option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={form.advisor}
                onChange={set('advisor')}
                placeholder="Ej: Dr. Carlos Alberto García Mendoza"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            )}
          </div>

          {/* Línea de investigación */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">Línea de investigación *</label>
            <select
              value={form.research_line}
              onChange={set('research_line')}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              {RESEARCH_LINES.map(l => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>

          {/* Ciudad y Año */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700 flex items-center gap-1.5">
                <MapPin size={14} /> Ciudad
              </label>
              <select
                value={form.city}
                onChange={set('city')}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                {CITIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700 flex items-center gap-1.5">
                <Calendar size={14} /> Año
              </label>
              <input
                type="number"
                value={form.year}
                onChange={set('year')}
                min={2020} max={2030}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Plantillas de referencia (múltiples) */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700 flex items-center gap-1.5">
              <FileUp size={14} /> Plantillas de referencia
              <span className="font-normal text-gray-400">(opcional, hasta 5 DOCX/PDF)</span>
            </label>

            {/* Lista de archivos subidos */}
            {templateFiles.length > 0 && (
              <div className="space-y-1.5">
                {templateFiles.map((f, idx) => (
                  <div key={idx} className="flex items-center gap-2 p-2.5 border border-emerald-200 rounded-lg bg-emerald-50">
                    <FileText size={16} className="text-emerald-600 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-emerald-800 truncate">{f.name}</p>
                      <p className="text-xs text-emerald-600">
                        {idx === 0 ? 'Estructura principal' : `Referencia ${idx + 1}`}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => removeTemplateFile(idx)}
                      className="p-1 text-gray-400 hover:text-red-500 transition-colors shrink-0"
                      title="Quitar"
                    >
                      <X size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Botón para añadir más (oculto si ya hay 5) */}
            {templateFiles.length < 5 && (
              <label className="flex items-center justify-center gap-2 w-full h-16 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-emerald-400 hover:bg-emerald-50 transition-colors">
                <FileUp size={18} className="text-gray-400" />
                <span className="text-xs text-gray-500">
                  {templateFiles.length === 0
                    ? 'Haz clic para subir plantilla DOCX o PDF'
                    : `Añadir otra plantilla (${templateFiles.length}/5)`}
                </span>
                <input
                  ref={templateInputRef}
                  type="file"
                  multiple
                  accept=".docx,.pdf,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  className="hidden"
                  onChange={handleTemplateChange}
                />
              </label>
            )}

            {templateFiles.length > 0 && (
              <p className="text-xs text-gray-500 bg-gray-50 rounded-lg px-3 py-2">
                La primera plantilla define la estructura principal. Las siguientes aportan secciones y tablas adicionales. Todas se fusionan para generar el documento.
              </p>
            )}
          </div>

          {/* Indicaciones para tablas, gráficos e imágenes */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700 flex items-center gap-1.5">
              <BarChart2 size={14} /> Indicaciones para tablas, gráficos e imágenes
              <span className="font-normal text-gray-400">(opcional)</span>
            </label>
            <textarea
              value={tableInstructions}
              onChange={e => {
                setTableInstructions(e.target.value)
                setElementsSummary(parseElementsSummary(e.target.value))
              }}
              rows={4}
              placeholder={`Ej: "Quiero 3 tablas: la primera con antecedentes nacionales, la segunda con antecedentes internacionales y la tercera con operacionalización de variables. También 2 gráficos de barras para comparar resultados y una imagen de la arquitectura del sistema."`}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500 resize-none"
            />
            {elementsSummary && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-xs text-amber-800 space-y-1">
                <p className="font-semibold">Elementos detectados:</p>
                <div className="flex flex-wrap gap-3">
                  {elementsSummary.tables > 0 && (
                    <span className="flex items-center gap-1">
                      <Table2 size={12} />
                      <b>{elementsSummary.tables}</b> tabla{elementsSummary.tables !== 1 ? 's' : ''}
                    </span>
                  )}
                  {elementsSummary.charts > 0 && (
                    <span className="flex items-center gap-1">
                      <BarChart2 size={12} />
                      <b>{elementsSummary.charts}</b> gráfico{elementsSummary.charts !== 1 ? 's' : ''}
                    </span>
                  )}
                  {elementsSummary.images > 0 && (
                    <span className="flex items-center gap-1">
                      <Image size={12} />
                      <b>{elementsSummary.images}</b> imagen{elementsSummary.images !== 1 ? 'es' : ''}
                    </span>
                  )}
                </div>
                <p className="text-amber-600">Se generarán e insertarán en el documento según lo indicado.</p>
              </div>
            )}
            {tableInstructions.trim() && !elementsSummary && (
              <p className="text-xs text-gray-500">Indica cantidades específicas (ej: "3 tablas", "dos gráficos") para ver el resumen.</p>
            )}
          </div>

          {/* Logo institucional */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700 flex items-center gap-1.5">
              <ImagePlus size={14} /> Logo institucional
              <span className="font-normal text-gray-400">(opcional, PNG/JPG)</span>
            </label>
            {logoPreview ? (
              <div className="flex items-center gap-3 p-2 border border-gray-200 rounded-lg bg-gray-50">
                <img src={logoPreview} alt="Logo" className="h-14 w-14 object-contain rounded" />
                <div className="flex-1 text-xs text-gray-500">Logo listo para insertar en la carátula</div>
                <button
                  type="button"
                  onClick={removeLogo}
                  className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                  title="Quitar logo"
                >
                  <X size={16} />
                </button>
              </div>
            ) : (
              <label className="flex flex-col items-center justify-center gap-1.5 w-full h-20 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors">
                <ImagePlus size={20} className="text-gray-400" />
                <span className="text-xs text-gray-500">Haz clic para seleccionar imagen</span>
                <input
                  ref={logoInputRef}
                  type="file"
                  accept="image/png,image/jpeg,image/jpg,image/webp"
                  className="hidden"
                  onChange={handleLogoChange}
                />
              </label>
            )}
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
              {error}
            </div>
          )}

          {/* Botón generar */}
          <button
            onClick={handleGenerate}
            disabled={loading || !valid}
            className={`w-full flex items-center justify-center gap-2 ${btnColorMap[activeType.color]} disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-lg transition-colors text-sm`}
          >
            {loading ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                Generando {docTypeLabel[docType]}... (puede tardar 30–90 s)
              </>
            ) : (
              <>
                <Sparkles size={18} />
                Generar {docTypeLabel[docType]}
              </>
            )}
          </button>

          {/* Info del tipo seleccionado */}
          <div className={`rounded-lg p-4 text-xs space-y-1 ${
            docType === 'tesis' ? 'bg-blue-50 text-blue-800' :
            docType === 'proyecto_tesis' ? 'bg-emerald-50 text-emerald-800' :
            'bg-violet-50 text-violet-800'
          }`}>
            <p className="font-semibold">Contenido generado:</p>
            {activeType.sections.map(s => <p key={s}>• {s}</p>)}
            {docType !== 'articulo' && (
              <p className="mt-1 font-medium">Arial Narrow 12 pt · Interlineado 1.5 · Márgenes 3/2.5 cm</p>
            )}
            {templateFiles.length > 0 && (
              <p className="mt-1 font-medium text-orange-700 bg-orange-100 rounded px-2 py-1">
                Con {templateFiles.length} plantilla{templateFiles.length > 1 ? 's' : ''}: estructura y tablas fusionadas
              </p>
            )}
          </div>
        </div>

        {/* ── RESULTADO ── */}
        <div className="space-y-4">
          {result ? (
            <>
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="font-semibold text-gray-800">{docTypeLabel[result.doc_type as DocType ?? 'tesis']} generado</h2>
                  <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                    result.source === 'openai'
                      ? 'bg-purple-100 text-purple-700'
                      : 'bg-green-100 text-green-700'
                  }`}>
                    {result.source === 'openai' ? '✨ GPT-4o' : '📋 Plantilla IA'}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  {activeType.sections.map(s => (
                    <div key={s} className="flex items-center gap-1.5 text-xs text-gray-600">
                      <span className="text-green-500 font-bold">✓</span> {s}
                    </div>
                  ))}
                  {templateFiles.length > 0 && (
                    <div className="col-span-2 flex items-center gap-1.5 text-xs text-emerald-700 bg-emerald-50 rounded px-2 py-1">
                      <span className="font-bold">✓</span> Estructura fusionada de {templateFiles.length} plantilla{templateFiles.length > 1 ? 's' : ''}
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-3 pt-2">
                  <button
                    onClick={() => handleDownload('pdf')}
                    className="flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 text-white font-semibold py-2.5 rounded-lg transition-colors text-sm"
                  >
                    <Download size={16} />
                    Descargar PDF
                  </button>
                  <button
                    onClick={() => handleDownload('docx')}
                    className="flex items-center justify-center gap-2 bg-blue-700 hover:bg-blue-800 text-white font-semibold py-2.5 rounded-lg transition-colors text-sm"
                  >
                    <Download size={16} />
                    Descargar Word
                  </button>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div className="px-5 py-3 border-b border-gray-100 flex items-center gap-2">
                  <FileText size={16} className="text-red-500" />
                  <span className="font-medium text-sm text-gray-700">Vista previa PDF</span>
                </div>
                {loadingPdf ? (
                  <div className="flex items-center justify-center h-64 text-gray-400 gap-2">
                    <Loader2 size={20} className="animate-spin" />
                    <span className="text-sm">Cargando previsualización...</span>
                  </div>
                ) : pdfUrl ? (
                  <iframe
                    src={pdfUrl}
                    title="Vista previa del documento"
                    className="w-full"
                    style={{ height: '520px', border: 'none' }}
                  />
                ) : (
                  <div className="flex items-center justify-center h-32 text-gray-400 text-sm">
                    No se pudo cargar la previsualización
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 flex flex-col items-center justify-center text-center text-gray-400 min-h-[400px] space-y-4">
              <BookOpen size={48} className="text-gray-200" />
              <div>
                <p className="font-medium text-gray-500">Completa el formulario y selecciona el tipo</p>
                <p className="text-sm mt-1">
                  El documento generado aparecerá aquí con su previsualización y botones de descarga.
                </p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 text-left text-xs text-gray-500 w-full max-w-xs space-y-1.5">
                <p className="font-semibold text-gray-600 mb-2">Tipos disponibles:</p>
                <p>🎓 <b>Tesis</b> — 5 capítulos completos, ≥ 50 págs.</p>
                <p>📋 <b>Proyecto de tesis</b> — propuesta con cronograma y presupuesto</p>
                <p>📰 <b>Artículo</b> — formato de publicación científica</p>
                <p className="mt-2 font-semibold text-gray-600">Con plantilla subida:</p>
                <p>📄 Analiza estructura y adapta secciones, tablas, matrices y gráficos al nuevo título</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
