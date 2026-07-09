export function sortIfDefined(a: Record<string, any>, b: Record<string, any>, key: string) {
  if (a[key] !== undefined && b[key] !== undefined) return b[key] - a[key]
  if (a[key] !== undefined) return -1
  if (b[key] !== undefined) return 1
  return a.id.localeCompare(b.id)
}

export function downloadTextFile(data: string, filename: string) {
  const blob = new Blob([data], { type: 'text/csv' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename + '.csv'
  a.click()
}

export function toRelativeTime(date: Date, locale: string) {
  const now = new Date().getTime()
  const diff = (now - date.getTime()) / 1000
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' })

  if (diff < 60) {
    return rtf.format(-Math.round(diff), 'second')
  } else if (diff < 3600) {
    return rtf.format(-Math.round(diff / 60), 'minute')
  } else if (diff < 86400) {
    return rtf.format(-Math.round(diff / 3600), 'hour')
  } else {
    return rtf.format(-Math.round(diff / 86400), 'day')
  }
}

export function toShortDate(date: Date, locale: string) {
  return date.toLocaleString(locale, { year: 'numeric', month: 'numeric' })
}
