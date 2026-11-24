import { useCallback, useEffect, useState } from 'react'

import { fetchCapabilities, fetchTools, fetchUserPreferences, updateUserPreferences } from '../api/services'
import { useSystemStatus } from '../hooks/useSystemStatus'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import type { CapabilitiesResponse, ToolCatalogResponse, UserPreferencesResponse } from '../types/api'

export function SettingsPage() {
  const system = useSystemStatus()
  const [prefs, setPrefs] = useState<UserPreferencesResponse | null>(null)
  const [tools, setTools] = useState<ToolCatalogResponse | null>(null)
  const [caps, setCaps] = useState<CapabilitiesResponse | null>(null)
  const [verbosity, setVerbosity] = useState('standard')
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const [preferences, catalog, capabilities] = await Promise.all([
        fetchUserPreferences(),
        fetchTools(),
        fetchCapabilities(),
      ])
      setPrefs(preferences)
      setVerbosity(preferences.preferences.verbosity ?? 'standard')
      setTools(catalog)
      setCaps(capabilities)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings.')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function savePreferences() {
    try {
      const updated = await updateUserPreferences({
        ...(prefs?.preferences ?? {}),
        verbosity,
      })
      setPrefs(updated)
      setMessage('Preferences saved.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save preferences.')
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-white">Settings</h1>
        <p className="mt-1 text-sm text-slate-400">System capabilities and agent preferences.</p>
      </header>
      {error ? <ErrorBanner message={error} onRetry={() => void load()} /> : null}
      {message ? <p className="text-sm text-emerald-300">{message}</p> : null}

      <Card title="Environment">
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-slate-500">Service</dt>
            <dd className="text-slate-200">{system.health?.service ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Version</dt>
            <dd className="text-slate-200">{system.health?.version ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Readiness</dt>
            <dd className="text-slate-200">{system.ready?.status ?? '—'}</dd>
          </div>
        </dl>
      </Card>

      <Card title="Agent preferences">
        <label className="block text-sm text-slate-400">
          Planner verbosity
          <select
            value={verbosity}
            onChange={(e) => setVerbosity(e.target.value)}
            className="mt-1 w-full max-w-xs rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200"
          >
            <option value="standard">Standard</option>
            <option value="brief">Brief</option>
          </select>
        </label>
        <Button className="mt-4" onClick={() => void savePreferences()}>
          Save preferences
        </Button>
      </Card>

      <Card title="Capabilities">
        <ul className="divide-y divide-slate-800">
          {(caps?.capabilities ?? []).map((cap) => (
            <li key={cap.name} className="flex justify-between gap-4 py-2 text-sm">
              <span className="text-slate-200">{cap.name}</span>
              <span className="text-slate-500">{cap.state}</span>
            </li>
          ))}
        </ul>
      </Card>

      <Card title="Registered tools" description={`${tools?.tools.length ?? 0} tools exposed to the agent.`}>
        <ul className="max-h-64 space-y-2 overflow-y-auto text-sm text-slate-400">
          {(tools?.tools ?? []).map((tool) => (
            <li key={tool.name} className="flex justify-between gap-2">
              <span className="font-mono text-slate-300">{tool.name}</span>
              <span className={tool.available ? 'text-emerald-400' : 'text-slate-600'}>
                {tool.available ? 'available' : 'off'}
              </span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}