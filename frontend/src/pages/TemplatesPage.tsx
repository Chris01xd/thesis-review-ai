import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getTemplates, saveTemplate, getPrograms } from '@/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input, Select, Textarea } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Dialog } from '@/components/ui/dialog'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { Plus, Edit2, BookOpen } from 'lucide-react'
import type { Template } from '@/types'

const BLANK: Partial<Template> = {
  name: '', version: '1.0', content: '',
  expected_sections: '', rubric_json: '', active: 1,
}

export default function TemplatesPage() {
  const qc = useQueryClient()
  const [dialog, setDialog] = useState(false)
  const [form, setForm] = useState<Partial<Template>>(BLANK)

  const { data: templates, isLoading } = useQuery({ queryKey: ['templates'], queryFn: getTemplates })
  const { data: programs } = useQuery({ queryKey: ['programs'], queryFn: getPrograms })

  const save = useMutation({
    mutationFn: () => saveTemplate(form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['templates'] }); setDialog(false) },
  })

  function openNew() { setForm(BLANK); setDialog(true) }
  function openEdit(t: Template) { setForm(t); setDialog(true) }

  return (
    <div>
      <div className="flex items-center justify-between flex-wrap gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Plantillas</h1>
          <p className="text-slate-500 text-sm mt-1">Gestiona las plantillas de evaluación del programa</p>
        </div>
        <Button onClick={openNew}><Plus size={16} /> Nueva plantilla</Button>
      </div>

      {isLoading && <LoadingSpinner />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {templates?.map((t) => (
          <Card key={t.id}>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle>{t.name}</CardTitle>
                  <p className="text-xs text-slate-500 mt-1">v{t.version} · {t.program_name ?? '—'}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={t.active ? 'success' : 'gray'}>{t.active ? 'Activa' : 'Inactiva'}</Badge>
                  <button onClick={() => openEdit(t)} className="p-1.5 rounded hover:bg-slate-100 text-slate-500">
                    <Edit2 size={14} />
                  </button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {t.expected_sections && (
                <div>
                  <p className="text-xs font-medium text-slate-600 mb-1">Secciones esperadas:</p>
                  <p className="text-xs text-slate-500">{t.expected_sections}</p>
                </div>
              )}
            </CardContent>
          </Card>
        ))}

        {templates?.length === 0 && (
          <div className="lg:col-span-2 flex flex-col items-center py-16 text-slate-400">
            <BookOpen size={48} className="mb-3 opacity-30" />
            <p>No hay plantillas registradas</p>
          </div>
        )}
      </div>

      <Dialog open={dialog} onClose={() => setDialog(false)} title={form.id ? 'Editar plantilla' : 'Nueva plantilla'} className="max-w-2xl">
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <Label>Nombre</Label>
              <Input value={form.name ?? ''} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Nombre de la plantilla" />
            </div>
            <div>
              <Label>Versión</Label>
              <Input value={form.version ?? ''} onChange={(e) => setForm({ ...form, version: e.target.value })} placeholder="1.0" />
            </div>
          </div>
          <div>
            <Label>Programa</Label>
            <Select value={String(form.program_id ?? '')} onChange={(e) => setForm({ ...form, program_id: Number(e.target.value) })}>
              <option value="">Seleccionar programa...</option>
              {programs?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </Select>
          </div>
          <div>
            <Label>Secciones esperadas (separadas por coma)</Label>
            <Input value={form.expected_sections ?? ''} onChange={(e) => setForm({ ...form, expected_sections: e.target.value })} placeholder="Introducción, Marco Teórico, ..." />
          </div>
          <div>
            <Label>Contenido / instrucciones</Label>
            <Textarea rows={4} value={form.content ?? ''} onChange={(e) => setForm({ ...form, content: e.target.value })} placeholder="Descripción y criterios de la plantilla..." />
          </div>
          <div>
            <Label>Rúbrica (JSON)</Label>
            <Textarea rows={3} value={form.rubric_json ?? ''} onChange={(e) => setForm({ ...form, rubric_json: e.target.value })} placeholder='{"nota_maxima": 20, ...}' />
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="active" checked={!!form.active} onChange={(e) => setForm({ ...form, active: e.target.checked ? 1 : 0 })} className="w-4 h-4" />
            <label htmlFor="active" className="text-sm text-slate-700">Plantilla activa</label>
          </div>
          {save.error && <p className="text-sm text-red-600">Error al guardar la plantilla</p>}
          <div className="flex gap-3 pt-2">
            <Button onClick={() => save.mutate()} loading={save.isPending} className="flex-1">Guardar</Button>
            <Button variant="outline" onClick={() => setDialog(false)}>Cancelar</Button>
          </div>
        </div>
      </Dialog>
    </div>
  )
}
