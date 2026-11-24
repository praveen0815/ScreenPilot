export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      className="flex flex-col gap-3 rounded-xl border border-red-500/30 bg-red-950/40 px-4 py-3 text-red-100 sm:flex-row sm:items-center sm:justify-between"
      role="alert"
    >
      <p className="text-sm">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="text-sm font-medium text-red-200 underline-offset-2 hover:underline"
        >
          Try again
        </button>
      ) : null}
    </div>
  )
}