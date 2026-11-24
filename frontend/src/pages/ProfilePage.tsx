import { useEffect, useState, type FormEvent } from 'react'

import { updateProfile } from '../api/services'
import { useAuth } from '../auth/AuthContext'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { formatDate } from '../lib/format'

export function ProfilePage() {
  const { user, refreshProfile } = useAuth()
  const [displayName, setDisplayName] = useState(user?.display_name ?? '')
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (user?.display_name) {
      setDisplayName(user.display_name)
    }
  }, [user?.display_name])

  if (!user) {
    return null
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSaved(false)
    try {
      await updateProfile(displayName.trim())
      await refreshProfile()
      setSaved(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Update failed.')
    }
  }

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-white">Profile</h1>
        <p className="mt-1 text-sm text-slate-400">Your ScreenPilot identity.</p>
      </header>
      {error ? <ErrorBanner message={error} /> : null}
      {saved ? <p className="text-sm text-emerald-300">Profile updated.</p> : null}
      <Card>
        <dl className="space-y-3 text-sm">
          <div>
            <dt className="text-slate-500">Email</dt>
            <dd className="text-slate-100">{user.email}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Role</dt>
            <dd className="capitalize text-slate-100">{user.role}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Member since</dt>
            <dd className="text-slate-100">{formatDate(user.created_at)}</dd>
          </div>
        </dl>
        <form className="mt-6 space-y-3 border-t border-slate-800 pt-6" onSubmit={(e) => void onSubmit(e)}>
          <label className="block text-sm">
            <span className="text-slate-400">Display name</span>
            <input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100"
              required
            />
          </label>
          <Button type="submit">Save</Button>
        </form>
      </Card>
    </div>
  )
}