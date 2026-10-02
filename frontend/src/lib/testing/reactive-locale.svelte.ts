// Test-only stand-in for the paraglide locale signal: lets tests flip the
// locale reactively the way the real runtime does when the language changes.
let locale = $state('fr')

export function getTestLocale(): string {
  return locale
}

export function setTestLocale(value: string): void {
  locale = value
}
