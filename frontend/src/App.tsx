import { useSystemStatus } from './hooks/useSystemStatus'

function StatusBadge({ status }: { status: 'ok' | 'up' | 'down' | 'ready' | 'not_ready' | 'unavailable' }) {
  const tone =
    status === 'ok' || status === 'up' || status === 'ready'
      ? 'bg-emerald-500/20 text-emerald-200 ring-emerald-400/40'
      : status === 'down' || status === 'not_ready'
        ? 'bg-amber-500/20 text-amber-100 ring-amber-400/30'
        : 'bg-slate-500/20 text-slate-200 ring-slate-400/20'
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-medium ring-1 ${tone}`}>
      {status}
    </span>
  )
}

export default function App() {
  const { health, ready, capabilities, loading, error, refresh } = useSystemStatus()

  return (
    <main className="mx-auto min-h-screen bg-slate-950 max-w-5xl px-6 py-12">
      <header className="mb-10 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm tracking-wide text-slate-400 uppercase">Phase 1 foundation</p>
          <h1 className="mt-2 text-4xl font-semibold text-white">ScreenPilot</h1>
          <p className="mt-3 max-w-2xl text-slate-300">
            API, boundaries, and operational surfaces for agent, automation, and vision work in
            later phases. This build does not execute autonomous tasks.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          className="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={loading}
        >
          {loading ? 'Refreshing…' : 'Refresh status'}
        </button>
      </header>

      {error ? (
        <section className="mb-6 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-100">
          <p className="font-medium">Failed to load system status.</p>
          <p className="mt-1 text-sm">{error}</p>
        </section>
      ) : null}

      <section className="grid gap-6 md:grid-cols-2">
        <article className="rounded-2xl border border-slate-700/80 bg-slate-900/70 p-6 shadow-xl shadow-slate-950/40">
          <h2 className="text-lg font-medium text-white">Process health</h2>
          <p className="mt-1 text-sm text-slate-400">Liveness without dependency checks.</p>
          <dl className="mt-5 space-y-3 text-sm">
            <div className="flex items-center justify-between gap-4">
              <dt className="text-slate-300">Status</dt>
              <dd>
                {health ? <StatusBadge status={health.status} /> : <span className="text-slate-500">…</span>}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-4">
              <dt className="text-slate-300">Service</dt>
              <dd className="text-slate-100">{health?.service ?? '—'}</dd>
            </div>
            <div className="flex items-center justify-between gap-4">
              <dt className="text-slate-300">Version</dt>
              <dd className="text-slate-100">{health?.version ?? '—'}</dd>
            </div>
          </dl>
        </article>

        <article className="rounded-2xl border border-slate-700/80 bg-slate-900/70 p-6 shadow-xl shadow-slate-950/40">
          <h2 className="text-lg font-medium text-white">Readiness</h2>
          <p className="mt-1 text-sm text-slate-400">PostgreSQL and Redis connectivity.</p>
          <dl className="mt-5 space-y-3 text-sm">
            <div className="flex items-center justify-between gap-4">
              <dt className="text-slate-300">Overall</dt>
              <dd>
                {ready ? (
                  <StatusBadge status={ready.status} />
                ) : (
                  <span className="text-slate-500">…</span>
                )}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-4">
              <dt className="text-slate-300">Database</dt>
              <dd>
                {ready ? (
                  <StatusBadge status={ready.checks.database.status} />
                ) : (
                  <span className="text-slate-500">…</span>
                )}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-4">
              <dt className="text-slate-300">Redis</dt>
              <dd>
                {ready ? (
                  <StatusBadge status={ready.checks.redis.status} />
                ) : (
                  <span className="text-slate-500">…</span>
                )}
              </dd>
            </div>
          </dl>
        </article>
      </section>

      <section className="mt-6 rounded-2xl border border-slate-700/80 bg-slate-900/70 p-6 shadow-xl shadow-slate-950/40">
        <h2 className="text-lg font-medium text-white">Engine boundaries</h2>
        <p className="mt-1 text-sm text-slate-400">Interfaces exist. Execution is disabled until later phases.</p>
        <ul className="mt-5 divide-y divide-slate-800">
          {(capabilities?.capabilities ?? []).map((item) => (
            <li key={item.name} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-medium text-slate-100">{item.name}</p>
                <p className="text-sm text-slate-400">{item.detail}</p>
              </div>
              <StatusBadge status={item.state} />
            </li>
          ))}
          {!capabilities?.capabilities.length && !loading ? (
            <li className="py-3 text-sm text-slate-400">No capability data returned.</li>
          ) : null}
        </ul>
      </section>
    </main>
  )
}