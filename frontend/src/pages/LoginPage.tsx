import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'
import { Button } from '../components/ui/Button'
import { ErrorBanner } from '../components/ui/ErrorBanner'

export function LoginPage() {
  const { isAuthenticated, login, register } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/'

  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (isAuthenticated) {
    return <Navigate to={from} replace />
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      if (mode === 'login') {
        await login(email, password)
      } else {
        await register(email, password, displayName || email.split('@')[0] || 'User')
      }
      navigate(from, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0a0f1a] px-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/60 p-8 shadow-2xl shadow-black/40">
        <p className="text-xs font-medium tracking-widest text-cyan-400 uppercase">ScreenPilot</p>
        <h1 className="mt-2 text-2xl font-semibold text-white">
          {mode === 'login' ? 'Sign in' : 'Create account'}
        </h1>
        <p className="mt-2 text-sm text-slate-400">
          Secure access to your agent tasks and approvals.
        </p>
        <div className="mt-6 flex gap-2 rounded-lg bg-slate-950 p-1">
          <button
            type="button"
            className={`flex-1 rounded-md py-2 text-sm font-medium ${mode === 'login' ? 'bg-slate-800 text-white' : 'text-slate-400'}`}
            onClick={() => setMode('login')}
          >
            Login
          </button>
          <button
            type="button"
            className={`flex-1 rounded-md py-2 text-sm font-medium ${mode === 'register' ? 'bg-slate-800 text-white' : 'text-slate-400'}`}
            onClick={() => setMode('register')}
          >
            Register
          </button>
        </div>
        {error ? (
          <div className="mt-4">
            <ErrorBanner message={error} />
          </div>
        ) : null}
        <form className="mt-6 space-y-4" onSubmit={(e) => void onSubmit(e)}>
          {mode === 'register' ? (
            <label className="block text-sm">
              <span className="text-slate-400">Display name</span>
              <input
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/40"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                autoComplete="name"
              />
            </label>
          ) : null}
          <label className="block text-sm">
            <span className="text-slate-400">Email</span>
            <input
              type="email"
              required
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/40"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
          </label>
          <label className="block text-sm">
            <span className="text-slate-400">Password</span>
            <input
              type="password"
              required
              minLength={mode === 'register' ? 12 : 1}
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/40"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            />
            {mode === 'register' ? (
              <span className="mt-1 block text-xs text-slate-500">Minimum 12 characters.</span>
            ) : null}
          </label>
          <Button type="submit" className="w-full" disabled={busy}>
            {busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Register'}
          </Button>
        </form>
      </div>
    </div>
  )
}