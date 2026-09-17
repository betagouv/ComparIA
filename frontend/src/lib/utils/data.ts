import type { ClassValue } from 'svelte/elements'

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

export type TableCol<Id extends string = string> = {
  id: Id
  label: string
  kind?: 'date' | 'number' | 'boolean'
  orderable?: boolean
  tooltip?: string
  colHeaderClass?: ClassValue
}
export type OrderingMethod = 'ascending' | 'descending'
export type SortOptions<Id extends string> = {
  method: OrderingMethod
  col: Id
  search: string
}
export function sortRows<
  Id extends string,
  Row extends { search: string } & Record<Id, any>,
  Col extends { id: Id; kind?: 'date' | 'number' | 'boolean' }
>(rows: Row[], cols: Col[], options: SortOptions<Id>): Row[] {
  const _search = options.search.toLowerCase()

  return rows
    .filter((row) => (!_search ? true : row.search.includes(_search)))
    .sort((x, y) => {
      const [a, b] = options.method === 'ascending' ? [y, x] : [x, y]
      const orderKind = cols.find((col) => col.id === options.col)?.kind ?? null
      switch (orderKind) {
        case 'number':
          return sortIfDefined(a, b, options.col)
        case 'date':
          return b[options.col] - a[options.col]
        case 'boolean':
          return a[options.col] && b[options.col] ? 0 : a[options.col] ? 1 : -1
        default:
          return a[options.col].localeCompare(b[options.col])
      }
    })
}

export function toSearchString(arr: string[]) {
  return arr.map((str) => str.toLowerCase()).join(' ')
}
