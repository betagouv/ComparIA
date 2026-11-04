import type { BotModelWithData, Commons } from '$lib/models'
import { render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import RankingTable from './RankingTable.svelte'

function model(id: string, rank: number, trust: [number, number], extra = {}) {
  return {
    id,
    human_id: id,
    search: id,
    consumption: 120,
    energy_class: 'B',
    params: 8,
    size_class: 'S',
    arch: 'dense',
    release_date: '2026-01-01',
    license: { kind: 'open-source' },
    lab: { name: 'Lab', logo: null, has_custom_logo: false },
    badges: { license: { text: 'Open source' } },
    data: {
      elo: 1200 - rank * 10,
      rank,
      rankClass: '1',
      score_p2_5: 1190 - rank * 10,
      score_p97_5: 1210 - rank * 10,
      trust_range: trust,
      n_match: 500
    },
    ...extra
  } as unknown as BotModelWithData
}

const commons = (greyRankSpread?: number) =>
  ({
    modelsCount: 3,
    currency: { code: 'EUR', rate: 1 },
    rankClasses: { 1: { min: 1, max: 3 } },
    platformName: 'Test',
    greyRankSpread
  }) as unknown as Commons

const models = [
  model('solid', 1, [0, 1]),
  model('loose', 2, [1, 12]),
  model('closed', 3, [2, 0], { license: { kind: 'proprietary' } })
]

function renderTable(greyRankSpread?: number) {
  return render(RankingTable, {
    id: 'ranking-table',
    models,
    commons: commons(greyRankSpread),
    lastUpdateDate: '01/01/2026',
    totalVotes: 1500,
    onDownloadData: () => {}
  })
}

const headers = (container: HTMLElement) =>
  [...container.querySelectorAll('thead th')].map((th) => th.id || th.textContent!.trim())

describe('RankingTable', () => {
  it('leaves the confidence, architecture, organisation and raw energy columns out', () => {
    const { container } = renderTable()
    const ids = container.querySelectorAll('thead th').length
    const text = container.querySelector('thead')!.textContent!

    expect(ids).toBeGreaterThan(0)
    expect(text).not.toContain('Confiance')
    expect(text).not.toContain('Architecture')
    expect(text).not.toContain('Organisation')
    expect(text).not.toContain('Conso. moyenne')
    expect(text).toContain('Énergie')
    expect(headers(container).length).toBe(8)
  })

  it('shows the rank range on hover over the score', () => {
    const { container } = renderTable()
    const row = container.querySelector('#ranking-table-loose')!

    expect(row.querySelector('[title]')!.getAttribute('title')).toBe('Rang possible entre 1 et 14')
  })

  it('shows the energy label, and N/A for proprietary models', () => {
    const { container } = renderTable()

    expect(container.querySelector('#ranking-table-solid')!.textContent).toContain('B')
    expect(container.querySelector('#ranking-table-closed')!.textContent).toContain('N/A')
  })

  it('greys out models whose rank could move more than the threshold', () => {
    const { container } = renderTable(10)

    expect(container.querySelector('#ranking-table-loose')!.classList).toContain('opacity-60')
    expect(container.querySelector('#ranking-table-solid')!.classList).not.toContain('opacity-60')
    expect(container.textContent).toContain('plus de 10 places')
  })

  it('greys out nothing without a threshold', () => {
    const { container } = renderTable()

    expect(container.querySelectorAll('tr.opacity-60')).toHaveLength(0)
    expect(container.textContent).not.toContain('places.')
  })
})
