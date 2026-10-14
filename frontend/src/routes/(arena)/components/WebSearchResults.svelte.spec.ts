import { render, screen } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import WebSearchResults from './WebSearchResults.svelte'

describe('WebSearchResults', () => {
  it('renders accessible source links without requiring favicons', () => {
    const { container } = render(WebSearchResults, {
      id: 'search-results',
      results: [
        {
          type: 'text',
          name: 'Source accessible',
          url: 'https://example.com/article',
          content: 'Result content'
        },
        {
          type: 'text',
          name: '',
          url: 'https://example.org',
          content: 'Other result',
          favicon: 'javascript:alert(1)'
        },
        {
          type: 'text',
          name: 'Unsafe source',
          url: 'javascript:alert(1)',
          content: 'Unsafe result'
        }
      ]
    })

    expect(screen.getByRole('button').getAttribute('aria-controls')).toBe('search-results')
    const namedSource = screen.getByRole('link', { name: 'Source accessible' })
    expect(namedSource.getAttribute('href')).toBe('https://example.com/article')
    expect(namedSource.getAttribute('rel')).toContain('noopener')
    expect(namedSource.getAttribute('target')).toBe('_blank')
    expect(screen.getByRole('link', { name: 'https://example.org' })).not.toBeNull()
    expect(screen.queryByRole('link', { name: 'Unsafe source' })).toBeNull()
    expect(container.querySelectorAll('img')).toHaveLength(0)
  })

  it('does not render an empty sources section', () => {
    const { container } = render(WebSearchResults, {
      id: 'empty-search-results',
      results: []
    })

    expect(container.querySelector('section')).toBeNull()
  })

  it('does not render a section containing only unsafe URLs', () => {
    const { container } = render(WebSearchResults, {
      id: 'unsafe-search-results',
      results: [
        {
          type: 'text',
          name: 'Unsafe source',
          url: 'javascript:alert(1)',
          content: 'Unsafe result'
        }
      ]
    })

    expect(container.querySelector('section')).toBeNull()
  })
})
