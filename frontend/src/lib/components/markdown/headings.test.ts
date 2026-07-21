import { describe, expect, it } from 'vitest'
import { normalizeDocumentHeadings } from './headings'

describe('normalizeDocumentHeadings', () => {
  it('starts document content at heading level two', () => {
    expect(normalizeDocumentHeadings('# Title\n\n## Section')).toBe('## Title\n\n## Section')
  })

  it('prevents skipped heading levels', () => {
    expect(normalizeDocumentHeadings('#### Section\n###### Detail')).toBe('## Section\n### Detail')
  })

  it('normalizes setext headings', () => {
    expect(normalizeDocumentHeadings('Section\n---')).toBe('## Section')
  })

  it('leaves headings inside code fences unchanged', () => {
    expect(normalizeDocumentHeadings('```md\n# Example\n```')).toBe('```md\n# Example\n```')
  })
})
