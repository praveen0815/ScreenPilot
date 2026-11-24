export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return '—'
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function truncate(text: string, max = 160): string {
  if (text.length <= max) {
    return text
  }
  return `${text.slice(0, max)}…`
}