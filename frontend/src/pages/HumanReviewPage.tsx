import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAdvances, getFindings, updateFinding } from '@/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Dialog } from '@/components/ui/dialog'
import { SeverityBadge } from '@/components/shared/SeverityBadge'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { Textarea } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { CheckCircle2, XCircle, MessageSquare } from 'lucide-react'
import { formatDate } from '@/lib/utils'
import type { Finding } from '@/types'

export default function HumanReviewPage() {
  const [selectedAdvId, setSelectedAdvId] = useState<number | null>(null)
  const [reviewDialog, setReviewDialog] = useState<Finding | null>(null)
  const [action, setAction] = useState('Aceptado')
  const [comment, setComment] = useState('')
  const qc = useQueryClient()

  const { data: advances, isLoading: loadAdv } = useQuery({
    queryKey: ['advances-review'],
    queryFn: () => getAdvances({ status: 'En revisión humana' }),
  })

  const { data: findings, isLoading: loadFind } = useQuery({
    queryKey: ['findings', selectedAdvId],
    queryFn: () => getFindings(selectedAdvId!),
    enabled: !!selectedAdvId,
  })

  const reviewMut = useMutation({
    mutationFn: () => updateFinding(reviewDialog!.id, { human_action: action, human_comment: comment }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['findings', selectedAdvId] })
      setReviewDialog(null)
      setComment('')
    },
  })

  const pending = findings?.filter((f) => !f.human_action || f.human_action === 'Pendiente')
  const reviewed = findings?.filter((f) => f.human_action && f.human_action !== 'Pendiente')

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Revisión Humana</h1>
        <p className="text-slate-500 text-sm mt-1">Valida o rechaza los hallazgos detectados por IA</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Advance selector */}
        <div>
          <Card>
            <CardHeader><CardTitle>Avances pendientes</CardTitle></CardHeader>
            <CardContent className="p-0">
              {loadAdv && <LoadingSpinner />}
              {advances?.length === 0 && (
                <p className="text-sm text-slate-400 text-center py-8">Sin avances pendientes de revisión</p>
              )}
              {advances?.map((adv) => (
                <button
                  key={adv.id}
                  onClick={() => setSelectedAdvId(adv.id)}
                  className={`w-full text-left px-4 py-3 border-b last:border-0 hover:bg-slate-50 transition-all ${selectedAdvId === adv.id ? 'bg-blue-50 border-l-4 border-l-blue-600' : ''}`}
                >
                  <p className="text-sm font-medium text-slate-800 line-clamp-2">{adv.title}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-slate-400">{formatDate(adv.created_at)}</span>
                    {adv.total_findings !== undefined && (
                      <Badge variant="warning">{adv.total_findings} hallazgos</Badge>
                    )}
                  </div>
                </button>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Findings */}
        <div className="lg:col-span-2">
          {!selectedAdvId && (
            <div className="flex items-center justify-center h-64 text-slate-400 text-sm">
              Selecciona un avance para revisar sus hallazgos
            </div>
          )}

          {selectedAdvId && loadFind && <LoadingSpinner />}

          {selectedAdvId && findings && (
            <div className="space-y-4">
              {/* Summary */}
              <div className="flex gap-3">
                <Badge variant="warning">{pending?.length} pendientes</Badge>
                <Badge variant="success">{reviewed?.length} revisados</Badge>
              </div>

              {/* Pending */}
              {pending?.map((f) => (
                <Card key={f.id}>
                  <CardContent className="py-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <SeverityBadge severity={f.severity} />
                          <Badge variant="gray">{f.type}</Badge>
                          {f.section_ref && <span className="text-xs text-slate-400">§ {f.section_ref}</span>}
                        </div>
                        <p className="text-sm text-slate-800">{f.description}</p>
                        {f.correction_steps && (
                          <p className="text-xs text-slate-500 mt-2">{f.correction_steps}</p>
                        )}
                      </div>
                      <Button
                        size="sm" variant="outline"
                        onClick={() => { setReviewDialog(f); setAction('Aceptado'); setComment('') }}
                      >
                        <MessageSquare size={14} /> Revisar
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}

              {/* Reviewed */}
              {reviewed?.map((f) => (
                <Card key={f.id} className="opacity-60">
                  <CardContent className="py-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        {f.human_action === 'Aceptado' ? <CheckCircle2 size={16} className="text-emerald-500" /> : <XCircle size={16} className="text-red-500" />}
                        <SeverityBadge severity={f.severity} />
                        <span className="text-sm text-slate-600 line-clamp-1">{f.description}</span>
                      </div>
                      <Badge variant={f.human_action === 'Aceptado' ? 'success' : 'error'}>{f.human_action}</Badge>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Review Dialog */}
      <Dialog open={!!reviewDialog} onClose={() => setReviewDialog(null)} title="Revisar hallazgo">
        {reviewDialog && (
          <div className="space-y-4">
            <div>
              <SeverityBadge severity={reviewDialog.severity} />
              <p className="text-sm text-slate-800 mt-2">{reviewDialog.description}</p>
            </div>
            <div>
              <Label>Acción</Label>
              <Select value={action} onChange={(e) => setAction(e.target.value)}>
                <option value="Aceptado">Aceptado — es correcto, el estudiante debe corregir</option>
                <option value="Rechazado">Rechazado — el hallazgo IA no aplica</option>
                <option value="En revisión">En revisión — requiere más análisis</option>
              </Select>
            </div>
            <div>
              <Label>Comentario (opcional)</Label>
              <Textarea
                rows={3}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Agrega un comentario o retroalimentación..."
              />
            </div>
            <div className="flex gap-3 pt-2">
              <Button onClick={() => reviewMut.mutate()} loading={reviewMut.isPending} className="flex-1">
                Guardar revisión
              </Button>
              <Button variant="outline" onClick={() => setReviewDialog(null)}>Cancelar</Button>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  )
}
