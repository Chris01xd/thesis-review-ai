import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Settings, Database, Brain, Globe, Key } from 'lucide-react'

export default function ConfigPage() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Configuración</h1>
        <p className="text-slate-500 text-sm mt-1">Información del sistema ThesisReview AI</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Database size={18} /> Base de datos</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <InfoRow label="Motor" value="SQLite 3" />
            <InfoRow label="Ruta" value="data/thesis_review.db" />
            <InfoRow label="Estado" value={<Badge variant="success">Conectada</Badge>} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Brain size={18} /> Motor IA</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <InfoRow label="Motor primario" value="Local (Agentic)" />
            <InfoRow label="Fallback" value="OpenAI GPT-4o-mini" />
            <InfoRow label="Estado IA" value={<Badge variant="success">Activo</Badge>} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Globe size={18} /> Integraciones externas</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <InfoRow label="CrossRef (DOI)" value={<Badge variant="info">Habilitado</Badge>} />
            <InfoRow label="ORCID" value={<Badge variant="info">Habilitado</Badge>} />
            <InfoRow label="Copyleaks" value={<Badge variant="gray">Configurado</Badge>} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Key size={18} /> API Backend</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <InfoRow label="Framework" value="FastAPI 0.115+" />
            <InfoRow label="Servidor" value="Uvicorn" />
            <InfoRow label="URL docs" value={<a href="http://localhost:8000/docs" target="_blank" rel="noopener" className="text-blue-600 hover:underline text-sm">localhost:8000/docs</a>} />
            <InfoRow label="Auth" value="Token demo (reemplazar por JWT)" />
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Settings size={18} /> Información del sistema</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <InfoRow label="Versión" value="v3.0.0" />
            <InfoRow label="Frontend" value="React 19 + Vite + Tailwind v4 + shadcn/ui" />
            <InfoRow label="Backend" value="Python + FastAPI + SQLite" />
            <InfoRow label="Móvil" value="React Native + Expo 54" />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-1 border-b border-slate-100 last:border-0">
      <span className="text-sm text-slate-500">{label}</span>
      <span className="text-sm font-medium text-slate-800">{value}</span>
    </div>
  )
}
