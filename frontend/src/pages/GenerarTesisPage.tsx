import { useState, useRef } from 'react'
import { FileText, Download, Loader2, Sparkles, BookOpen, User, Users, MapPin, Calendar, ImagePlus, X } from 'lucide-react'
import { generateThesis, downloadThesisFile, getThesisPdfBlob } from '../api'
import type { ThesisResult } from '../api'

const RESEARCH_LINES = [
  'Gestión de Sistemas de Información',
  'Inteligencia Artificial y Machine Learning',
  'Seguridad Informática y Ciberseguridad',
  'Desarrollo de Software',
  'Redes y Comunicaciones',
  'Ingeniería de Software y Metodologías Ágiles',
  'Big Data y Ciencia de Datos',
  'Internet de las Cosas (IoT)',
  'Automatización y Robótica',
  'Gestión de Tecnologías de Información',
  'Computación en la Nube y DevOps',
  'Sistemas Embebidos y Microcontroladores',
]

const CITIES = ['Trujillo', 'Lima', 'Arequipa', 'Chiclayo', 'Piura', 'Cusco', 'Iquitos', 'Huancayo']

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

export default function GenerarTesisPage() {
  const [form, setForm]           = useState<FormState>(INITIAL)
  const [loading, setLoading]     = useState(false)
  const [result, setResult]       = useState<ThesisResult | null>(null)
  const [error, setError]         = useState('')
  const [pdfUrl, setPdfUrl]       = useState('')
  const [loadingPdf, setLoadingPdf] = useState(false)
  const [logoData, setLogoData]   = useState<string>('')      // base64 data-URL
  const [logoPreview, setLogoPreview] = useState<string>('')  // object URL for <img>
  const logoInputRef = useRef<HTMLInputElement>(null)

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

  const removeLogo = () => {
    setLogoData('')
    setLogoPreview('')
    if (logoInputRef.current) logoInputRef.current.value = ''
  }

  const valid = form.title.trim() && form.authors.trim() && form.advisor.trim()

  const handleGenerate = async () => {
    if (!valid) return
    setLoading(true)
    setError('')
    setResult(null)
    setPdfUrl('')
    try {
      const res = await generateThesis({
        title:         form.title.trim(),
        authors:       form.authors.trim(),
        advisor:       form.advisor.trim(),
        research_line: form.research_line,
        city:          form.city,
        year:          form.year,
        logo_data:     logoData || undefined,
      })
      setResult(res)
      // Load PDF preview
      setLoadingPdf(true)
      try {
        const url = await getThesisPdfBlob(res.pdf_file)
        setPdfUrl(url)
      } finally {
        setLoadingPdf(false)
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Error al generar la tesis'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = (type: 'pdf' | 'docx') => {
    if (!result) return
    const file = type === 'pdf' ? result.pdf_file : result.docx_file
    downloadThesisFile(file)
  }

  return (
    <div className="space-y-6 p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-blue-100 rounded-lg">
          <BookOpen className="text-blue-700" size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Generador de Tesis</h1>
          <p className="text-sm text-gray-500">
            Genera automáticamente el contenido estructurado de tu tesis en PDF y Word
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ── FORMULARIO ── */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-5">
          <div className="flex items-center gap-2 pb-2 border-b border-gray-100">
            <Sparkles size={18} className="text-blue-600" />
            <h2 className="font-semibold text-gray-800">Datos de la tesis</h2>
          </div>

          {/* Título */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700 flex items-center gap-1.5">
              <FileText size={14} /> Título de la tesis *
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
              placeholder="Ej: Juan Carlos Pérez López, María Elena Rodríguez Sánchez"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Asesor */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700 flex items-center gap-1.5">
              <User size={14} /> Asesor *
            </label>
            <input
              type="text"
              value={form.advisor}
              onChange={set('advisor')}
              placeholder="Ej: Dr. Carlos Alberto García Mendoza"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Línea de investigación */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">Línea de investigación *</label>
            <select
              value={form.research_line}
              onChange={set('research_line')}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              {RESEARCH_LINES.map(l => (
                <option key={l} value={l}>{l}</option>
              ))}
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
            className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-lg transition-colors text-sm"
          >
            {loading ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                Generando tesis... (puede tardar 30-60 s)
              </>
            ) : (
              <>
                <Sparkles size={18} />
                Generar tesis completa
              </>
            )}
          </button>

          {/* Especificaciones */}
          <div className="bg-blue-50 rounded-lg p-4 text-xs text-blue-800 space-y-1">
            <p className="font-semibold text-blue-900">Formato generado:</p>
            <p>• Arial Narrow 12 pt · Interlineado 1.5 · Justificado</p>
            <p>• Márgenes: Izq 3 cm / Der-Sup-Inf 2.5 cm</p>
            <p>• Numeración arábiga esquina inferior derecha</p>
            <p>• Cap. I–V completos · ≥ 50 páginas</p>
            <p>• Máx. 25 referencias APA V7 · 80% inglés · 80% últimos 5 años</p>
            <p>• Logo institucional en carátula (si se sube)</p>
          </div>
        </div>

        {/* ── RESULTADO ── */}
        <div className="space-y-4">
          {result ? (
            <>
              {/* Badges de estado */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="font-semibold text-gray-800">Tesis generada</h2>
                  <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                    result.source === 'openai'
                      ? 'bg-purple-100 text-purple-700'
                      : 'bg-green-100 text-green-700'
                  }`}>
                    {result.source === 'openai' ? '✨ GPT-4o' : '📋 Plantilla IA'}
                  </span>
                </div>

                {/* Secciones generadas */}
                <div className="grid grid-cols-2 gap-2">
                  {[
                    'Resumen / Abstract', 'Cap. I: Introducción',
                    'Realidad problemática', 'Antecedentes', 'Marco teórico',
                    'Cap. II: Metodología', 'Cap. III: Resultados',
                    'Cap. IV: Discusión', 'Cap. V: Conclusiones',
                    'Máx. 25 refs APA V7', 'Árbol de problemas', 'Declaración jurada',
                  ].map(s => (
                    <div key={s} className="flex items-center gap-1.5 text-xs text-gray-600">
                      <span className="text-green-500 font-bold">✓</span> {s}
                    </div>
                  ))}
                </div>

                {/* Botones de descarga */}
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

              {/* Vista previa PDF */}
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
                    title="Vista previa de tesis"
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
                <p className="font-medium text-gray-500">Completa el formulario</p>
                <p className="text-sm mt-1">
                  La tesis generada aparecerá aquí con su previsualización y botones de descarga.
                </p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 text-left text-xs text-gray-500 w-full max-w-xs space-y-1.5">
                <p className="font-semibold text-gray-600 mb-2">Contenido generado (≥ 50 páginas):</p>
                <p>📄 Carátula con logo · Jurado · Índices</p>
                <p>📝 Resumen y Abstract</p>
                <p>📗 Cap. I: Introducción completa</p>
                <p>📘 Cap. II: Metodología detallada</p>
                <p>📊 Cap. III: Resultados con tablas</p>
                <p>💬 Cap. IV: Discusión</p>
                <p>✅ Cap. V: Conclusiones y Recomendaciones</p>
                <p>📚 Máx. 25 referencias APA V7</p>
                <p>🌳 Árboles de problemas y objetivos</p>
                <p>✍️ Declaración jurada</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
