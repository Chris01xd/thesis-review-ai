import { useState, useRef, type ChangeEvent } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { uploadAdvance, getStudents } from '@/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input, Select } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { Upload, FileText, X, CheckCircle2 } from 'lucide-react'

const ADVANCE_TYPES = ['Capítulo I', 'Capítulo II', 'Capítulo III', 'Capítulo IV', 'Capítulo V', 'Proyecto de Tesis', 'Informe Final']

export default function UploadPage() {
  const navigate = useNavigate()
  const fileRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [studentId, setStudentId] = useState('')
  const [advanceType, setAdvanceType] = useState(ADVANCE_TYPES[0])
  const [version, setVersion] = useState('1')
  const [autoAnalyze, setAutoAnalyze] = useState(true)
  const [success, setSuccess] = useState<number | null>(null)

  const { data: students } = useQuery({ queryKey: ['students'], queryFn: getStudents })

  const upload = useMutation({
    mutationFn: () => {
      const fd = new FormData()
      fd.append('file', file!)
      fd.append('title', title)
      fd.append('student_id', studentId)
      fd.append('advance_type', advanceType)
      fd.append('version', version)
      fd.append('auto_analyze', autoAnalyze ? '1' : '0')
      return uploadAdvance(fd)
    },
    onSuccess: (data) => setSuccess(data.advance_id),
  })

  function handleFile(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (f) {
      setFile(f)
      if (!title) setTitle(f.name.replace(/\.[^.]+$/, '').replace(/[_-]/g, ' '))
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    const f = e.dataTransfer.files[0]
    if (f) { setFile(f); if (!title) setTitle(f.name.replace(/\.[^.]+$/, '').replace(/[_-]/g, ' ')) }
  }

  if (success !== null) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <CheckCircle2 size={56} className="text-emerald-500 mb-4" />
        <h2 className="text-xl font-bold text-slate-800 mb-2">Avance cargado exitosamente</h2>
        <p className="text-slate-500 text-sm mb-6">
          {autoAnalyze ? 'El análisis IA está en progreso.' : 'El avance fue guardado como Pendiente.'}
        </p>
        <div className="flex gap-3">
          <Button onClick={() => navigate(`/advances/${success}`)}>Ver avance</Button>
          <Button variant="outline" onClick={() => { setSuccess(null); setFile(null); setTitle('') }}>
            Cargar otro
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Cargar Avance</h1>
        <p className="text-slate-500 text-sm mt-1">Sube un documento de tesis para análisis IA</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* File drop zone */}
        <Card>
          <CardHeader><CardTitle>Documento</CardTitle></CardHeader>
          <CardContent>
            <div
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
              onClick={() => fileRef.current?.click()}
              className="border-2 border-dashed border-slate-300 rounded-xl p-8 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-all"
            >
              {file ? (
                <div>
                  <FileText size={36} className="mx-auto text-blue-600 mb-2" />
                  <p className="font-medium text-slate-800">{file.name}</p>
                  <p className="text-xs text-slate-500 mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); setFile(null) }}
                    className="mt-3 text-xs text-red-500 hover:text-red-700 flex items-center gap-1 mx-auto"
                  >
                    <X size={12} /> Quitar archivo
                  </button>
                </div>
              ) : (
                <div>
                  <Upload size={36} className="mx-auto text-slate-400 mb-3" />
                  <p className="text-sm font-medium text-slate-700">Arrastra tu archivo aquí</p>
                  <p className="text-xs text-slate-400 mt-1">o haz clic para seleccionar</p>
                  <p className="text-xs text-slate-400 mt-2">PDF, DOCX o TXT · máx. 20 MB</p>
                </div>
              )}
            </div>
            <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" className="hidden" onChange={handleFile} />
          </CardContent>
        </Card>

        {/* Form */}
        <Card>
          <CardHeader><CardTitle>Información del avance</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="title">Título del avance</Label>
              <Input id="title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Ej: Capítulo I - Introducción" />
            </div>
            <div>
              <Label htmlFor="student">Estudiante</Label>
              <Select id="student" value={studentId} onChange={(e) => setStudentId(e.target.value)}>
                <option value="">Seleccionar estudiante...</option>
                {students?.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="adv_type">Tipo de avance</Label>
              <Select id="adv_type" value={advanceType} onChange={(e) => setAdvanceType(e.target.value)}>
                {ADVANCE_TYPES.map((t) => <option key={t}>{t}</option>)}
              </Select>
            </div>
            <div>
              <Label htmlFor="version">Versión</Label>
              <Input id="version" type="number" min="1" max="10" value={version} onChange={(e) => setVersion(e.target.value)} className="w-24" />
            </div>
            <div className="flex items-center gap-3 pt-1">
              <input
                type="checkbox"
                id="auto_analyze"
                checked={autoAnalyze}
                onChange={(e) => setAutoAnalyze(e.target.checked)}
                className="w-4 h-4 rounded text-blue-600"
              />
              <label htmlFor="auto_analyze" className="text-sm text-slate-700 cursor-pointer">
                Iniciar análisis IA automáticamente
              </label>
            </div>

            {upload.error && (
              <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">
                {(upload.error as Error).message ?? 'Error al cargar el avance'}
              </div>
            )}

            <Button
              onClick={() => upload.mutate()}
              loading={upload.isPending}
              disabled={!file || !title || !studentId}
              className="w-full"
            >
              <Upload size={16} />
              {autoAnalyze ? 'Cargar y analizar' : 'Cargar avance'}
            </Button>
          </CardContent>
        </Card>
      </div>

      {upload.isPending && (
        <div className="mt-4">
          <LoadingSpinner text="Procesando documento y ejecutando análisis IA..." />
        </div>
      )}
    </div>
  )
}
