import { NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '../../auth/AuthContext'
import { Button } from '../ui/Button'

const nav = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/chat', label: 'Agent chat' },
  { to: '/tasks', label: 'Task history' },
  { to: '/approvals', label: 'Approvals' },
  { to: '/settings', label: 'Settings' },
  { to: '/profile', label: 'Profile' },
]

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-2 text-sm font-medium transition ${
    isActive
      ? 'bg-cyan-500/15 text-cyan-300'
      : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
  }`

export function AppShell() {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-[#0a0f1a] text-slate-200">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col lg:flex-row">
        <aside className="border-b border-slate-800/80 lg:w-56 lg:border-b-0 lg:border-r">
          <div className="flex items-center justify-between gap-3 px-5 py-5 lg:flex-col lg:items-stretch">
            <div>
              <p className="text-xs font-medium tracking-widest text-cyan-400/80 uppercase">ScreenPilot</p>
              <h1 className="text-lg font-semibold text-white">Agent Console</h1>
            </div>
            <p className="hidden text-xs text-slate-500 lg:block">{user?.display_name}</p>
          </div>
          <nav className="flex gap-1 overflow-x-auto px-3 pb-4 lg:flex-col" aria-label="Main">
            {nav.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end} className={linkClass}>
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="hidden px-3 pb-6 lg:block">
            <Button variant="ghost" className="w-full" onClick={() => void logout()}>
              Sign out
            </Button>
          </div>
        </aside>
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}