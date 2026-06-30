'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { signOut, useSession } from 'next-auth/react'
import { cn } from '@/lib/utils'

const nav = [
  { href: '/dashboard',           label: 'Overview',     icon: '📊' },
  { href: '/dashboard/leads',     label: 'Leads',        icon: '👥' },
  { href: '/dashboard/campaigns', label: 'Campaigns',    icon: '🚀' },
  { href: '/dashboard/approval',  label: 'Approval Queue', icon: '✅' },
  { href: '/dashboard/inbox',     label: 'Inbox',        icon: '📨' },
  { href: '/dashboard/analytics', label: 'Analytics',    icon: '📈' },
  { href: '/dashboard/settings',  label: 'Settings',     icon: '⚙️' },
]

export function Sidebar() {
  const pathname = usePathname()
  const { data: session } = useSession()

  return (
    <aside className="w-60 flex flex-col border-r border-slate-200 bg-white">
      {/* Logo */}
      <div className="h-16 flex items-center px-5 border-b border-slate-200">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <span className="font-bold text-slate-900">Gojiberry</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {nav.map((item) => {
          const active = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href))
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                active
                  ? 'bg-brand-50 text-brand-700'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              )}
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
            </Link>
          )
        })}
      </nav>

      {/* User */}
      <div className="p-3 border-t border-slate-200">
        <div className="flex items-center gap-3 px-2 py-2">
          <div className="w-7 h-7 bg-brand-100 rounded-full flex items-center justify-center flex-shrink-0">
            <span className="text-xs font-semibold text-brand-700">
              {session?.user?.email?.[0]?.toUpperCase() || '?'}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-slate-900 truncate">{session?.user?.email}</p>
          </div>
          <button
            onClick={() => signOut({ callbackUrl: '/auth/signin' })}
            className="text-slate-400 hover:text-slate-600"
            title="Sign out"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </div>
    </aside>
  )
}
