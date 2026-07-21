export function normalizeDocumentHeadings(markdown: string): string {
  const lines = markdown.split('\n')
  const output: string[] = []
  let previousLevel = 1
  let fence: { marker: string; length: number } | undefined

  for (const line of lines) {
    const fenceMatch = line.match(/^ {0,3}(`{3,}|~{3,})/)
    if (fenceMatch) {
      const marker = fenceMatch[1][0]
      if (!fence) fence = { marker, length: fenceMatch[1].length }
      else if (fence.marker === marker && fenceMatch[1].length >= fence.length) fence = undefined
      output.push(line)
      continue
    }

    if (fence) {
      output.push(line)
      continue
    }

    const heading = line.match(/^( {0,3})(#{1,6})(\s+.*)$/)
    if (heading) {
      const requestedLevel = Math.max(2, heading[2].length)
      const level = Math.min(requestedLevel, previousLevel + 1, 6)
      previousLevel = level
      output.push(`${heading[1]}${'#'.repeat(level)}${heading[3]}`)
      continue
    }

    if (/^ {0,3}(?:=+|-+)\s*$/.test(line) && output.at(-1)?.trim()) {
      const title = output.pop()?.trim() ?? ''
      previousLevel = 2
      output.push(`## ${title}`)
      continue
    }

    output.push(line)
  }

  return output.join('\n')
}
