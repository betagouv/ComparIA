/**
 * Accessibility regression tests for the shared data table.
 *
 * The ranking page mounts two of these at once (tab panels stay in the DOM),
 * which is what made the id collisions below real rather than theoretical.
 * These assertions run without a backend, unlike the ranking page itself.
 */
import { render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import { expectAccessible, expectNoDuplicateIds } from '$lib/testing/a11y'
import TableHarness from './Table.harness.svelte'

const cols = [
  { id: 'name', label: 'Modèle', orderable: true },
  { id: 'elo', label: 'Score <sup>BT</sup>', orderable: true },
  { id: 'org', label: 'Organisation' }
]
const rows = [
  { id: 'a', name: 'Alpha', elo: '1200', org: 'Lab A' },
  { id: 'b', name: 'Beta', elo: '1100', org: 'Lab B' }
]

describe('Table', () => {
  it('declares its column headers and their sort state', async () => {
    const { container } = render(TableHarness, {
      id: 'ranking-table',
      caption: 'Classement des modèles',
      cols,
      rows,
      orderingCol: 'elo',
      orderingMethod: 'descending'
    })

    const headers = [...container.querySelectorAll('th')]
    expect(headers.every((th) => th.getAttribute('scope') === 'col')).toBe(true)

    const [name, elo, org] = headers
    // aria-sort belongs on the cell, and sortable-but-unsorted reports 'none'
    // rather than staying silent.
    expect(elo.getAttribute('aria-sort')).toBe('descending')
    expect(name.getAttribute('aria-sort')).toBe('none')
    expect(org.getAttribute('aria-sort')).toBeNull()

    await expectAccessible(container)
  })

  it('names each sort button after its column', () => {
    const { container } = render(TableHarness, {
      id: 'ranking-table',
      caption: 'Classement des modèles',
      cols,
      rows
    })

    const names = [...container.querySelectorAll('th button')].map(
      (b) => b.textContent?.trim() ?? ''
    )

    expect(names).toHaveLength(2)
    expect(new Set(names).size).toBe(2) // not all "Trier"
    expect(names[0]).toContain('Modèle')
    // markup in the column label must not leak into the accessible name
    expect(names[1]).toContain('Score BT')
    expect(names[1]).not.toContain('<sup>')
  })

  it('keeps its ids apart when two tables are on the page', () => {
    const { container: first } = render(TableHarness, {
      id: 'ranking-table',
      caption: 'Classement',
      cols,
      rows,
      search: ''
    })
    const { container: second } = render(TableHarness, {
      id: 'energy-table',
      caption: 'Consommation',
      cols,
      rows,
      search: ''
    })

    const page = document.createElement('div')
    page.append(first.cloneNode(true), second.cloneNode(true))
    expectNoDuplicateIds(page)
  })

  it('titles each table distinctly', () => {
    const { container: first } = render(TableHarness, {
      id: 'ranking-table',
      caption: 'Classement des modèles',
      cols,
      rows
    })
    const { container: second } = render(TableHarness, {
      id: 'energy-table',
      caption: 'Données du graphique en tableau',
      cols,
      rows
    })

    const captions = [first, second].map((c) => c.querySelector('caption')?.textContent?.trim())
    expect(new Set(captions).size).toBe(2)
  })
})
