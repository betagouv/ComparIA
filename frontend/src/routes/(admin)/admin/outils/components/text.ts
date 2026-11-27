// Tool names and descriptions are kept per language. Lists show the instance's
// default one, else whichever was written.
export function defaultText(texts: Record<string, string> | null | undefined, locale: string) {
  if (!texts) return ''
  return texts[locale] || Object.values(texts).find(Boolean) || ''
}
