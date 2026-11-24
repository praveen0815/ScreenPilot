import type { ButtonHTMLAttributes } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'

const styles: Record<Variant, string> = {
  primary:
    'bg-cyan-500 text-slate-950 hover:bg-cyan-400 focus-visible:ring-cyan-400/60 disabled:bg-cyan-900/40 disabled:text-slate-500',
  secondary:
    'bg-slate-800 text-slate-100 hover:bg-slate-700 ring-1 ring-slate-600/50 focus-visible:ring-cyan-400/40',
  ghost: 'text-slate-300 hover:bg-slate-800/80 hover:text-white',
  danger: 'bg-red-600/90 text-white hover:bg-red-500 focus-visible:ring-red-400/50',
}

export function Button({
  variant = 'primary',
  className = '',
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 disabled:cursor-not-allowed disabled:opacity-50 ${styles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}