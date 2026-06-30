import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function tierColor(tier: string) {
  switch (tier) {
    case 'Hot':  return 'text-red-600 bg-red-50 border-red-200'
    case 'Warm': return 'text-amber-600 bg-amber-50 border-amber-200'
    default:     return 'text-slate-500 bg-slate-50 border-slate-200'
  }
}

export function statusColor(status: string) {
  const map: Record<string, string> = {
    new:          'bg-blue-100 text-blue-700',
    contacted:    'bg-purple-100 text-purple-700',
    replied:      'bg-green-100 text-green-700',
    booked:       'bg-emerald-100 text-emerald-700',
    disqualified: 'bg-slate-100 text-slate-500',
  }
  return map[status] || 'bg-slate-100 text-slate-500'
}

export function formatScore(n: number) {
  return Math.round(n)
}

export function truncate(s: string, n: number) {
  return s.length > n ? s.slice(0, n) + '…' : s
}
