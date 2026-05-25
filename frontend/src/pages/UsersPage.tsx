import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getUsers, createUser, updateUser, deleteUser, getPrograms } from '@/api'
import client from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input, Select, Textarea } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Dialog } from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { Plus, Edit2, Trash2, Search, ExternalLink, CheckCircle2, XCircle, AlertCircle } from 'lucide-react'
import type { User } from '@/types'

const ROLE_COLORS = { ADMIN: 'error', COORDINATOR: 'warning', ADVISOR: 'info', STUDENT: 'success' } as const
const BLANK: Partial<User> & { password: string; expertise: string } = {
  name: '', email: '', role: 'STUDENT', password: '', orcid_id: '', affiliation: '', expertise: '',
}

type Tab = 'list' | 'create' | 'assign' | 'orcid'

export default function UsersPage() {
  const [tab, setTab] = useState<Tab>('list')

  const tabs: { key: Tab; label: string }[] = [
    { key: 'list',   label: 'Listado de usuarios' },
    { key: 'create', label: 'Registrar usuario' },
    { key: 'assign', label: 'Asignar asesor' },
    { key: 'orcid',  label: 'ORCID / Expertise' },
  ]

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Usuarios, roles y ORCID</h1>
        <p className="text-slate-500 text-sm mt-1">Gestiona cuentas, asignaciones y perfiles de asesores</p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 mb-5 border-b border-slate-200 overflow-x-auto">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-all -mb-px whitespace-nowrap ${
              tab === t.key
                ? 'border-blue-600 text-blue-700'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'list'   && <UserListTab />}
      {tab === 'create' && <CreateUserTab onCreated={() => setTab('list')} />}
      {tab === 'assign' && <AssignAdvisorTab />}
      {tab === 'orcid'  && <OrcidTab />}
    </div>
  )
}

/* ── Tab 1: Listado ──────────────────────────────────────────────────────── */
function UserListTab() {
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [editDialog, setEditDialog] = useState<User | null>(null)
  const [confirmDel, setConfirmDel] = useState<User | null>(null)
  const [form, setForm] = useState<Partial<User> & { password: string; expertise: string }>(BLANK)

  const { data: users, isLoading } = useQuery({ queryKey: ['users'], queryFn: () => getUsers() })
  const { data: programs } = useQuery({ queryKey: ['programs'], queryFn: getPrograms })
  const { data: advisors } = useQuery({ queryKey: ['advisors'], queryFn: () => getUsers('ADVISOR') })

  const updateMut = useMutation({
    mutationFn: () => updateUser(form.id!, { ...form, ...(form.password ? {} : { password: undefined }) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); setEditDialog(null) },
  })
  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteUser(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); setConfirmDel(null) },
  })

  const filtered = users?.filter((u) =>
    `${u.name} ${u.email} ${u.role} ${u.program ?? ''} ${u.orcid_id ?? ''}`.toLowerCase().includes(search.toLowerCase()),
  )

  function openEdit(u: User) {
    setForm({ ...u, password: '', expertise: u.expertise ?? '' })
    setEditDialog(u)
  }

  return (
    <>
      <Card>
        <div className="p-4 border-b border-slate-100">
          <div className="relative max-w-sm">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <Input placeholder="Buscar usuario..." className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
        </div>
        {isLoading && <LoadingSpinner />}
        {filtered && (
          <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>#</TableHead>
                <TableHead>Nombre</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Rol</TableHead>
                <TableHead>Programa</TableHead>
                <TableHead>Asesor</TableHead>
                <TableHead>ORCID</TableHead>
                <TableHead>Afiliación</TableHead>
                <TableHead>Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((u) => (
                <TableRow key={u.id}>
                  <TableCell className="text-slate-400">{u.id}</TableCell>
                  <TableCell className="font-medium text-slate-800">{u.name}</TableCell>
                  <TableCell className="text-slate-500">{u.email}</TableCell>
                  <TableCell><Badge variant={ROLE_COLORS[u.role]}>{u.role}</Badge></TableCell>
                  <TableCell className="text-slate-500">{u.program ?? '—'}</TableCell>
                  <TableCell className="text-slate-500">{u.advisor ?? '—'}</TableCell>
                  <TableCell>
                    {u.orcid_id
                      ? <a href={`https://orcid.org/${u.orcid_id}`} target="_blank" rel="noopener" className="text-xs text-blue-600 hover:underline flex items-center gap-1"><ExternalLink size={11} />{u.orcid_id}</a>
                      : <span className="text-slate-300 text-xs">—</span>}
                  </TableCell>
                  <TableCell className="text-slate-500 text-xs max-w-[140px] truncate">{u.affiliation ?? '—'}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <button onClick={() => openEdit(u)} className="p-1.5 rounded hover:bg-slate-100 text-slate-500"><Edit2 size={14} /></button>
                      <button onClick={() => setConfirmDel(u)} className="p-1.5 rounded hover:bg-red-50 text-red-400"><Trash2 size={14} /></button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          </div>
        )}
      </Card>

      {/* Edit dialog */}
      <Dialog open={!!editDialog} onClose={() => setEditDialog(null)} title="Editar usuario">
        <UserFormFields
          form={form} setForm={setForm}
          programs={programs ?? []}
          advisors={advisors ?? []}
          isEdit
        />
        {updateMut.error && <p className="text-sm text-red-600 mt-2">Error al guardar</p>}
        <div className="flex gap-3 mt-4">
          <Button onClick={() => updateMut.mutate()} loading={updateMut.isPending} disabled={!form.name || !form.email} className="flex-1">Guardar cambios</Button>
          <Button variant="outline" onClick={() => setEditDialog(null)}>Cancelar</Button>
        </div>
      </Dialog>

      {/* Delete confirm */}
      <Dialog open={!!confirmDel} onClose={() => setConfirmDel(null)} title="Confirmar eliminación">
        {confirmDel && (
          <div>
            <p className="text-sm text-slate-700 mb-4">¿Eliminar a <strong>{confirmDel.name}</strong>? Esta acción no se puede deshacer.</p>
            <div className="flex gap-3">
              <Button variant="destructive" loading={deleteMut.isPending} onClick={() => deleteMut.mutate(confirmDel.id)} className="flex-1">Eliminar</Button>
              <Button variant="outline" onClick={() => setConfirmDel(null)}>Cancelar</Button>
            </div>
          </div>
        )}
      </Dialog>
    </>
  )
}

/* ── Tab 2: Registrar ────────────────────────────────────────────────────── */
function CreateUserTab({ onCreated }: { onCreated: () => void }) {
  const qc = useQueryClient()
  const [form, setForm] = useState<Partial<User> & { password: string; expertise: string }>(BLANK)
  const { data: programs } = useQuery({ queryKey: ['programs'], queryFn: getPrograms })
  const { data: advisors } = useQuery({ queryKey: ['advisors'], queryFn: () => getUsers('ADVISOR') })

  const createMut = useMutation({
    mutationFn: () => createUser({ ...form, password: form.password || '123456' } as Required<typeof form>),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); setForm(BLANK); onCreated() },
  })

  return (
    <Card className="max-w-xl">
      <CardHeader><CardTitle>Registrar nuevo usuario</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <UserFormFields form={form} setForm={setForm} programs={programs ?? []} advisors={advisors ?? []} />
        {createMut.error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {(createMut.error as Error).message ?? 'Error al registrar'}
          </p>
        )}
        <Button onClick={() => createMut.mutate()} loading={createMut.isPending} disabled={!form.name || !form.email} className="w-full">
          <Plus size={16} /> Registrar usuario
        </Button>
      </CardContent>
    </Card>
  )
}

/* ── Tab 3: Asignar asesor ───────────────────────────────────────────────── */
function AssignAdvisorTab() {
  const qc = useQueryClient()
  const [studentId, setStudentId] = useState('')
  const [advisorId, setAdvisorId] = useState('')
  const [success, setSuccess] = useState(false)

  const { data: students } = useQuery({ queryKey: ['students-list'], queryFn: () => getUsers('STUDENT') })
  const { data: advisors } = useQuery({ queryKey: ['advisors'], queryFn: () => getUsers('ADVISOR') })

  const assignMut = useMutation({
    mutationFn: () => updateUser(Number(studentId), { advisor_id: Number(advisorId) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
    },
  })

  if (!students?.length) return <div className="text-slate-400 text-sm py-8">No hay estudiantes registrados.</div>
  if (!advisors?.length)  return <div className="text-slate-400 text-sm py-8">No hay asesores registrados.</div>

  return (
    <Card className="max-w-md">
      <CardHeader><CardTitle>Asignar o cambiar asesor</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <div>
          <Label>Alumno</Label>
          <Select value={studentId} onChange={(e) => setStudentId(e.target.value)}>
            <option value="">Seleccionar alumno...</option>
            {students.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.email})</option>)}
          </Select>
        </div>
        <div>
          <Label>Asesor</Label>
          <Select value={advisorId} onChange={(e) => setAdvisorId(e.target.value)}>
            <option value="">Seleccionar asesor...</option>
            {advisors.map((a) => <option key={a.id} value={a.id}>{a.name} ({a.email})</option>)}
          </Select>
        </div>
        {success && (
          <div className="flex items-center gap-2 text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">
            <CheckCircle2 size={16} /> Asesor asignado correctamente.
          </div>
        )}
        <Button
          onClick={() => assignMut.mutate()}
          loading={assignMut.isPending}
          disabled={!studentId || !advisorId}
          className="w-full"
        >
          Guardar asignación
        </Button>
      </CardContent>
    </Card>
  )
}

/* ── Tab 4: ORCID / Expertise ────────────────────────────────────────────── */
function OrcidTab() {
  const qc = useQueryClient()
  const [selectedId, setSelectedId] = useState<string>('')
  const [orcidForm, setOrcidForm] = useState({ orcid_id: '', affiliation: '', expertise: '' })
  const [thesisTitle, setThesisTitle] = useState('Sistema web inteligente de gestión y predicción de desperdicio alimentario')
  const [expertiseResult, setExpertiseResult] = useState<{ score: number; compatible: boolean; analysis: string; keywords: string[]; engine: string } | null>(null)
  const [validatingExpertise, setValidatingExpertise] = useState(false)
  const [orcidResult, setOrcidResult] = useState<{ name?: string; bio?: string; works?: number; demo?: boolean; message?: string; error?: string } | null>(null)
  const [verifying, setVerifying] = useState(false)
  const [profileSaved, setProfileSaved] = useState(false)
  const [copyleaksResult, setCopyleaksResult] = useState<{ configured?: boolean; connected?: boolean; email?: string; credits?: number | null; message?: string; error?: string } | null>(null)
  const [verifyingCopyleaks, setVerifyingCopyleaks] = useState(false)

  const { data: advisors } = useQuery({ queryKey: ['advisors'], queryFn: () => getUsers('ADVISOR') })

  const selected = advisors?.find((a) => String(a.id) === selectedId)

  function handleSelectAdvisor(id: string) {
    setSelectedId(id)
    setOrcidResult(null)
    setExpertiseResult(null)
    setProfileSaved(false)
    const adv = advisors?.find((a) => String(a.id) === id)
    if (adv) {
      setOrcidForm({
        orcid_id: adv.orcid_id ?? '',
        affiliation: adv.affiliation ?? '',
        expertise: adv.expertise ?? '',
      })
    }
  }

  const saveMut = useMutation({
    mutationFn: () => updateUser(Number(selectedId), {
      orcid_id: orcidForm.orcid_id || undefined,
      affiliation: orcidForm.affiliation || undefined,
      expertise: orcidForm.expertise || undefined,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['advisors'] }); setProfileSaved(true); setTimeout(() => setProfileSaved(false), 3000) },
  })

  async function validateExpertise() {
    if (!orcidForm.expertise || !thesisTitle) return
    setValidatingExpertise(true)
    setExpertiseResult(null)
    try {
      const res = await client.post('/api/expertise/validate', {
        thesis_title: thesisTitle,
        expertise: orcidForm.expertise,
      })
      setExpertiseResult(res.data)
    } catch {
      setExpertiseResult({ score: 0, compatible: false, analysis: 'Error al conectar con el servidor.', keywords: [], engine: 'error' })
    } finally {
      setValidatingExpertise(false)
    }
  }

  async function verifyCopyleaks() {
    setVerifyingCopyleaks(true)
    setCopyleaksResult(null)
    try {
      const res = await client.get('/api/copyleaks/verify')
      setCopyleaksResult(res.data)
    } catch (e: unknown) {
      const axiosErr = e as { response?: { data?: { detail?: string } } }
      const msg = axiosErr?.response?.data?.detail ?? 'No se pudo conectar al servidor.'
      setCopyleaksResult({ error: msg })
    } finally {
      setVerifyingCopyleaks(false)
    }
  }

  async function verifyOrcid() {
    if (!orcidForm.orcid_id) return
    setVerifying(true)
    setOrcidResult(null)
    try {
      const res = await client.get(`/api/orcid/verify/${encodeURIComponent(orcidForm.orcid_id)}`)
      setOrcidResult(res.data)
    } catch (e: unknown) {
      const axiosErr = e as { response?: { data?: { detail?: string }; status?: number } }
      const msg = axiosErr?.response?.data?.detail
        ?? (axiosErr?.response?.status === 404 ? 'ORCID no encontrado. Verifica que el ID sea correcto.' : null)
        ?? 'No se pudo conectar al servidor. Verifica que el backend esté corriendo.'
      setOrcidResult({ error: msg })
    } finally {
      setVerifying(false)
    }
  }

  if (!advisors?.length) return <div className="text-slate-400 text-sm py-8">No hay asesores registrados.</div>

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Left: profile editor */}
      <Card>
        <CardHeader><CardTitle>Perfil del asesor</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label>Asesor</Label>
            <Select value={selectedId} onChange={(e) => handleSelectAdvisor(e.target.value)}>
              <option value="">Seleccionar asesor...</option>
              {advisors.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </Select>
          </div>

          {selected && (
            <>
              <div>
                <Label>ORCID iD</Label>
                <Input
                  value={orcidForm.orcid_id}
                  onChange={(e) => setOrcidForm({ ...orcidForm, orcid_id: e.target.value })}
                  placeholder="0000-0000-0000-0000"
                />
              </div>
              <div>
                <Label>Afiliación institucional</Label>
                <Input
                  value={orcidForm.affiliation}
                  onChange={(e) => setOrcidForm({ ...orcidForm, affiliation: e.target.value })}
                  placeholder="Universidad Nacional de Trujillo"
                />
              </div>
              <div>
                <Label>Líneas de investigación / expertise</Label>
                <Textarea
                  rows={3}
                  value={orcidForm.expertise}
                  onChange={(e) => setOrcidForm({ ...orcidForm, expertise: e.target.value })}
                  placeholder="desarrollo de software, inteligencia artificial, sistemas web..."
                />
              </div>
              {profileSaved && (
                <div className="flex items-center gap-2 text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">
                  <CheckCircle2 size={15} /> Perfil actualizado correctamente.
                </div>
              )}
              <Button onClick={() => saveMut.mutate()} loading={saveMut.isPending} className="w-full">
                Actualizar perfil del asesor
              </Button>
            </>
          )}
        </CardContent>
      </Card>

      {/* Right: verification */}
      <div className="space-y-4">
        {/* Expertise validator */}
        <Card>
          <CardHeader><CardTitle>Validar expertise</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div>
              <Label>Título de tesis para validación semántica</Label>
              <Input
                value={thesisTitle}
                onChange={(e) => setThesisTitle(e.target.value)}
                placeholder="Título de la tesis..."
              />
            </div>
            <Button variant="outline" onClick={validateExpertise} loading={validatingExpertise} disabled={!selected || !orcidForm.expertise} className="w-full">
              Validar con IA
            </Button>
            {expertiseResult && (
              <div className={`border rounded-lg p-3 space-y-2 ${expertiseResult.compatible ? 'bg-emerald-50 border-emerald-200' : 'bg-amber-50 border-amber-200'}`}>
                {/* Score bar */}
                <div className="flex items-center gap-3">
                  <div className="flex-1 bg-white/60 rounded-full h-2 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${expertiseResult.score >= 70 ? 'bg-emerald-500' : expertiseResult.score >= 40 ? 'bg-amber-400' : 'bg-red-400'}`}
                      style={{ width: `${expertiseResult.score}%` }}
                    />
                  </div>
                  <span className={`text-sm font-bold tabular-nums ${expertiseResult.compatible ? 'text-emerald-700' : 'text-amber-700'}`}>
                    {expertiseResult.score}%
                  </span>
                </div>
                {/* Verdict */}
                <div className={`flex items-center gap-2 font-medium text-sm ${expertiseResult.compatible ? 'text-emerald-700' : 'text-amber-700'}`}>
                  {expertiseResult.compatible ? <CheckCircle2 size={15} /> : <AlertCircle size={15} />}
                  {expertiseResult.compatible ? 'Asesor compatible con la tesis' : 'Compatibilidad baja — validar manualmente'}
                </div>
                {/* Analysis */}
                {expertiseResult.analysis && (
                  <p className="text-xs text-slate-600 leading-relaxed">{expertiseResult.analysis}</p>
                )}
                {/* Keywords */}
                {expertiseResult.keywords.length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-1">
                    {expertiseResult.keywords.map((kw) => (
                      <span key={kw} className="text-xs bg-white/70 border border-slate-200 rounded px-1.5 py-0.5 text-slate-600">{kw}</span>
                    ))}
                  </div>
                )}
                {/* Engine badge */}
                <p className="text-xs text-slate-400 text-right">Motor: {expertiseResult.engine}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* ORCID verifier */}
        <Card>
          <CardHeader><CardTitle>Verificar ORCID público</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {!selected && <p className="text-sm text-slate-400">Selecciona un asesor para verificar su ORCID.</p>}
            {selected && !orcidForm.orcid_id && (
              <p className="text-sm text-slate-400">Guarda primero un ORCID en el perfil del asesor.</p>
            )}
            {selected && orcidForm.orcid_id && (
              <>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-slate-600">ID:</span>
                  <code className="text-sm bg-slate-100 px-2 py-0.5 rounded">{orcidForm.orcid_id}</code>
                  <a
                    href={`https://orcid.org/${orcidForm.orcid_id}`}
                    target="_blank" rel="noopener"
                    className="text-blue-600 hover:text-blue-800 flex items-center gap-1 text-xs"
                  >
                    <ExternalLink size={13} /> Ver en orcid.org
                  </a>
                </div>
                <Button variant="outline" onClick={verifyOrcid} loading={verifying} className="w-full">
                  Verificar en ORCID Registry
                </Button>
                {orcidResult && !orcidResult.error && (
                  <div className={`border rounded-lg p-3 space-y-1 ${orcidResult.demo ? 'bg-amber-50 border-amber-200' : 'bg-emerald-50 border-emerald-200'}`}>
                    <div className={`flex items-center gap-2 font-medium text-sm ${orcidResult.demo ? 'text-amber-700' : 'text-emerald-700'}`}>
                      {orcidResult.demo ? <AlertCircle size={15} /> : <CheckCircle2 size={15} />}
                      {orcidResult.demo ? 'Modo demo — ORCID_ENABLED=false' : 'ORCID válido'}
                    </div>
                    {orcidResult.message && <p className="text-xs text-amber-700">{orcidResult.message}</p>}
                    {orcidResult.name && !orcidResult.demo && <p className="text-sm text-slate-700">Nombre registrado: <strong>{orcidResult.name}</strong></p>}
                    {orcidResult.bio  && <p className="text-xs text-slate-500 italic">{orcidResult.bio.slice(0, 300)}{orcidResult.bio.length > 300 ? '…' : ''}</p>}
                    {orcidResult.works !== undefined && <p className="text-xs text-slate-500">Publicaciones en ORCID: {orcidResult.works}</p>}
                  </div>
                )}
                {orcidResult?.error && (
                  <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                    <XCircle size={15} /> {orcidResult.error}
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
        {/* Copyleaks verifier */}
        <Card>
          <CardHeader><CardTitle>Verificar Copyleaks</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-slate-500">
              Comprueba si la integración con Copyleaks está activa y cuántos créditos quedan disponibles.
            </p>
            <Button variant="outline" onClick={verifyCopyleaks} loading={verifyingCopyleaks} className="w-full">
              Probar conexión con Copyleaks
            </Button>
            {copyleaksResult && !copyleaksResult.error && (
              <div className={`border rounded-lg p-3 space-y-1 ${copyleaksResult.connected ? 'bg-emerald-50 border-emerald-200' : 'bg-amber-50 border-amber-200'}`}>
                <div className={`flex items-center gap-2 font-medium text-sm ${copyleaksResult.connected ? 'text-emerald-700' : 'text-amber-700'}`}>
                  {copyleaksResult.connected ? <CheckCircle2 size={15} /> : <AlertCircle size={15} />}
                  {copyleaksResult.connected ? 'Conexión exitosa' : 'No configurado'}
                </div>
                {copyleaksResult.message && <p className="text-xs text-slate-600">{copyleaksResult.message}</p>}
                {copyleaksResult.email && <p className="text-xs text-slate-500">Cuenta: <strong>{copyleaksResult.email}</strong></p>}
                {copyleaksResult.connected && (
                  <p className="text-xs text-slate-500">
                    Créditos disponibles: <strong>{copyleaksResult.credits ?? 'No disponible'}</strong>
                  </p>
                )}
              </div>
            )}
            {copyleaksResult?.error && (
              <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                <XCircle size={15} /> {copyleaksResult.error}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

/* ── Shared form fields ──────────────────────────────────────────────────── */
function UserFormFields({
  form, setForm, programs, advisors, isEdit = false,
}: {
  form: Partial<User> & { password: string; expertise: string }
  setForm: (f: typeof form) => void
  programs: { id: number; name: string }[]
  advisors: User[]
  isEdit?: boolean
}) {
  return (
    <div className="space-y-3">
      <div>
        <Label>Nombres y apellidos</Label>
        <Input value={form.name ?? ''} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </div>
      <div>
        <Label>Correo institucional</Label>
        <Input type="email" value={form.email ?? ''} onChange={(e) => setForm({ ...form, email: e.target.value })} />
      </div>
      <div>
        <Label>Contraseña {isEdit && <span className="text-slate-400 font-normal">(dejar vacío para no cambiar)</span>}</Label>
        <Input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder={isEdit ? '' : '123456'} />
      </div>
      <div>
        <Label>Rol</Label>
        <Select value={form.role ?? 'STUDENT'} onChange={(e) => setForm({ ...form, role: e.target.value as User['role'] })}>
          <option value="STUDENT">Estudiante</option>
          <option value="ADVISOR">Asesor</option>
          <option value="COORDINATOR">Coordinador</option>
          <option value="ADMIN">Administrador</option>
        </Select>
      </div>
      <div>
        <Label>Programa académico</Label>
        <Select value={String(form.program_id ?? '')} onChange={(e) => setForm({ ...form, program_id: Number(e.target.value) || null })}>
          <option value="">Sin programa</option>
          {programs.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </Select>
      </div>
      {form.role === 'STUDENT' && (
        <div>
          <Label>Asesor asignado</Label>
          <Select value={String(form.advisor_id ?? '')} onChange={(e) => setForm({ ...form, advisor_id: Number(e.target.value) || null })}>
            <option value="">Sin asesor</option>
            {advisors.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </Select>
        </div>
      )}
      <div>
        <Label>ORCID <span className="text-slate-400 font-normal">(solo si es asesor)</span></Label>
        <Input value={form.orcid_id ?? ''} onChange={(e) => setForm({ ...form, orcid_id: e.target.value })} placeholder="0000-0000-0000-0000" />
      </div>
      <div>
        <Label>Afiliación institucional</Label>
        <Input value={form.affiliation ?? ''} onChange={(e) => setForm({ ...form, affiliation: e.target.value })} placeholder="Universidad Nacional de Trujillo" />
      </div>
      <div>
        <Label>Líneas de investigación / expertise</Label>
        <Textarea
          rows={2}
          value={form.expertise ?? ''}
          onChange={(e) => setForm({ ...form, expertise: e.target.value })}
          placeholder="desarrollo de software, inteligencia artificial..."
        />
      </div>
    </div>
  )
}
