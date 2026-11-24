export function LoadingScreen({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0a0f1a] text-slate-300">
      <div className="flex flex-col items-center gap-4">
        <div
          className="h-10 w-10 animate-spin rounded-full border-2 border-cyan-500/30 border-t-cyan-400"
          role="status"
          aria-label={label}
        />
        <p className="text-sm text-slate-400">{label}</p>
      </div>
    </div>
  )
}