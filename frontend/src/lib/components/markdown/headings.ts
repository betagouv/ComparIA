const FENCE = /^ {0,3}(`{3,}|~{3,})/
const ATX = /^ {0,3}(#{1,6})(\s+.*)$/
const SETEXT = /^ {0,3}(?:=+|-+)\s*$/

export function normalizeDocumentHeadings(markdown: string): string {
  const output: string[] = []
  let previousLevel = 1
  let fence: { marker: string; length: number } | undefined

  for (const line of markdown.split('\n')) {
    const fenceMatch = line.match(FENCE)
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

    const heading = line.match(ATX)
    if (heading) {
      previousLevel = Math.min(Math.max(2, heading[1].length), previousLevel + 1)
      output.push(`${'#'.repeat(previousLevel)}${heading[2]}`)
      continue
    }

    const previous = output.at(-1)?.trim()
    if (previous && !previous.startsWith('#') && SETEXT.test(line)) {
      output.pop()
      previousLevel = 2
      output.push(`## ${previous}`)
      continue
    }

    output.push(line)
  }

  return output.join('\n')
}
