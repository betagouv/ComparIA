import { describe, expect, it } from 'vitest'
import { normalizeDocumentHeadings, stripLeadingTitle } from './headings'

describe('stripLeadingTitle', () => {
  it('drops the title the page already displays', () => {
    expect(stripLeadingTitle('# Conditions\n\n## Objet')).toBe('## Objet')
  })

  it('leaves a document that starts with a section alone', () => {
    expect(stripLeadingTitle('## Objet\n\n# Conditions')).toBe('## Objet\n\n# Conditions')
  })
})

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

  it('leaves a thematic break after a heading alone', () => {
    expect(normalizeDocumentHeadings('# Title\n---')).toBe('## Title\n---')
  })

  it('leaves headings inside code fences unchanged', () => {
    expect(normalizeDocumentHeadings('```md\n# Example\n```')).toBe('```md\n# Example\n```')
  })
})
