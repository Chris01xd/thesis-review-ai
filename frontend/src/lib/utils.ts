import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('es-PE', {
    year: 'numeric', month: 'short', day: 'numeric',
  })
}

export function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString('es-PE', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export function gradeColor(grade: number | null): string {
  if (grade === null) return 'text-slate-400'
  if (grade >= 17) return 'text-emerald-600'
  if (grade >= 14) return 'text-blue-600'
  if (grade >= 11) return 'text-amber-600'
  return 'text-red-600'
}

export function scoreColor(score: number | null): string {
  if (score === null) return 'text-slate-400'
  if (score >= 80) return 'text-emerald-600'
  if (score >= 60) return 'text-blue-600'
  if (score >= 40) return 'text-amber-600'
  return 'text-red-600'
}
