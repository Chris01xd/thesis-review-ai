import { NavLink } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard, Users, FileText, Upload, ClipboardCheck, Layers,
  BarChart2, FileDown, Settings, BookOpen, UserCog, ScrollText, LogOut, X,
  PenLine, ShieldCheck, Bot,
} from 'lucide-react'
import type { Role } from '@/types'

interface NavItem {
  to: string
  label: string
  icon: React.ReactNode
  roles: Role[]
}

const NAV: NavItem[] = [
  { to: '/',              label: 'Dashboard',       icon: <LayoutDashboard size={18} />, roles: ['ADMIN','COORDINATOR','ADVISOR','STUDENT'] },
  { to: '/students',      label: 'Estudiantes',     icon: <Users size={18} />,           roles: ['ADMIN','COORDINATOR','ADVISOR'] },
  { to: '/advances',      label: 'Avances',         icon: <FileText size={18} />,        roles: ['ADMIN','COORDINATOR','ADVISOR','STUDENT'] },
  { to: '/upload',        label: 'Cargar Avance',   icon: <Upload size={18} />,          roles: ['ADMIN','COORDINATOR','ADVISOR'] },
  { to: '/review',        label: 'Revisión Humana', icon: <ClipboardCheck size={18} />,  roles: ['ADMIN','COORDINATOR','ADVISOR'] },
  { to: '/batch',         label: 'Rev. por Lotes',  icon: <Layers size={18} />,          roles: ['ADMIN','COORDINATOR','ADVISOR'] },
  { to: '/statistics',    label: 'Estadísticas',    icon: <BarChart2 size={18} />,       roles: ['ADMIN','COORDINATOR','ADVISOR'] },
  { to: '/reports',       label: 'Reportes',        icon: <FileDown size={18} />,        roles: ['ADMIN','COORDINATOR','ADVISOR'] },
  { to: '/templates',     label: 'Plantillas',      icon: <BookOpen size={18} />,        roles: ['ADMIN','COORDINATOR'] },
  { to: '/users',         label: 'Usuarios',        icon: <UserCog size={18} />,         roles: ['ADMIN','COORDINATOR'] },
  { to: '/audit',         label: 'Auditoría',       icon: <ScrollText size={18} />,      roles: ['ADMIN','COORDINATOR'] },
  { to: '/config',        label: 'Configuración',   icon: <Settings size={18} />,        roles: ['ADMIN'] },
  { to: '/generar-tesis', label: 'Generar Tesis',   icon: <PenLine size={18} />,         roles: ['ADMIN','COORDINATOR','ADVISOR','STUDENT'] },
  { to: '/similitud',     label: 'Similitud Acad.', icon: <ShieldCheck size={18} />,     roles: ['ADMIN','COORDINATOR','ADVISOR','STUDENT'] },
  { to: '/detector-ia',  label: 'Detector IA',     icon: <Bot size={18} />,             roles: ['ADMIN','COORDINATOR','ADVISOR','STUDENT'] },
]

interface SidebarProps {
  open: boolean
  onClose: () => void
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const { user, logout } = useAuth()
  if (!user) return null

  const visible = NAV.filter((n) => n.roles.includes(user.role))

  const roleLabel: Record<Role, string> = {
    ADMIN: 'Administrador', COORDINATOR: 'Coordinador',
    ADVISOR: 'Asesor', STUDENT: 'Estudiante',
  }

  return (
    <aside className={cn(
      'sidebar-gradient w-64 flex flex-col shrink-0 transition-transform duration-300 ease-in-out',
      'fixed inset-y-0 left-0 z-40 min-h-screen',
      open ? 'translate-x-0' : '-translate-x-full',
      'lg:relative lg:translate-x-0',
    )}>
      {/* Logo + close button */}
      <div className="px-5 py-5 border-b border-white/10 flex items-start justify-between">
        <div>
          <div className="text-white font-bold text-lg leading-tight">ThesisReview AI</div>
          <div className="text-blue-300 text-xs mt-0.5">Sistema de revisión de tesis</div>
        </div>
        <button
          onClick={onClose}
          className="lg:hidden p-1.5 rounded-lg text-white/60 hover:bg-white/10 hover:text-white mt-0.5"
          aria-label="Cerrar menú"
        >
          <X size={18} />
        </button>
      </div>

      {/* User info */}
      <div className="px-4 py-3 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold text-sm shrink-0">
            {user.name.charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0">
            <div className="text-white text-sm font-medium truncate">{user.name}</div>
            <div className="text-blue-300 text-xs">{roleLabel[user.role]}</div>
          </div>
        </div>
      </div>

      {/* Nav links */}
      <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
        {visible.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            onClick={onClose}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all',
                isActive
                  ? 'bg-white/20 text-white'
                  : 'text-white/75 hover:bg-white/10 hover:text-white',
              )
            }
          >
            {item.icon}
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* Logout */}
      <div className="px-3 py-4 border-t border-white/10">
        <button
          onClick={logout}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm text-white/70 hover:bg-white/10 hover:text-white transition-all"
        >
          <LogOut size={18} />
          Cerrar sesión
        </button>
      </div>
    </aside>
  )
}
