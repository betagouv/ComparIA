import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import type { BotModel, Commons, PersonalRow } from '$lib/models'
import PersonalTable from './PersonalTable.svelte'

const commons = { modelsCount: 2, currency: { code: 'EUR' }, rankClasses: {} } as Commons

/** Only the fields the table reads. */
const model = {
  id: 'a',
  human_id: 'mistral-large',
  size_class: 'L',
  params: 123,
  arch: 'dense',
  license: { kind: 'open-source' },
  lab: { name: 'Mistral', logo: 'mistral' }
} as BotModel

const rows: PersonalRow[] = [
  {
    id: 'a',
    llm_id: 'a',
    name: 'Mistral Large',
    rank: 1,
    score: 0.866,
    battles: 20,
    wins: 18,
    losses: 2,
    ties: 0,
    model,
    generalRank: 4,
    search: 'mistral-large'
  },
  {
    id: 'gone',
    llm_id: 'gone',
    name: 'Retired model',
    rank: 2,
    score: 0.667,
    battles: 1,
    wins: 1,
    losses: 0,
    ties: 0,
    model: null,
    generalRank: null,
    search: 'Retired model'
  },
  {
    id: 'c',
    llm_id: 'c',
    name: 'Third model',
    rank: 3,
    score: 0.5,
    battles: 50,
    wins: 25,
    losses: 25,
    ties: 0,
    model: { ...model, id: 'c', human_id: 'third-model' },
    generalRank: 2,
    search: 'third-model'
  }
]

const ranks = (container: HTMLElement) =>
  [...container.querySelectorAll('tbody tr td:first-child')].map((cell) => cell.textContent?.trim())

describe('personal ranking table', () => {
  it('shows the record beside the score, and nothing where there is no general rank', () => {
    const { container } = render(PersonalTable, {
      id: 'personal-ranking-table',
      rows,
      commons,
      votesCount: 21,
      onDownloadData: () => {}
    })

    const cells = [...container.querySelectorAll('tbody tr')].map((row) =>
      [...row.querySelectorAll('td')].map((cell) => cell.textContent?.trim())
    )

    expect(cells[0].slice(0, 6)).toEqual(['1', 'mistral-large', '0,866', '20', '18-2-0', '4'])
    expect(cells[1].slice(2, 6)).toEqual(['0,667', '1', '1-0-0', ''])
  })

  it('keeps a model that has left the arena, without a link to its card', () => {
    const { getByText } = render(PersonalTable, {
      id: 'personal-ranking-table',
      rows,
      commons,
      votesCount: 21,
      onDownloadData: () => {}
    })

    const name = getByText('Retired model')
    expect(name).toBeTruthy()
    expect(name.closest('a')).toBeNull()
  })

  it('sorts by score descending, and comes back to it once a column is cycled through', async () => {
    const { container } = render(PersonalTable, {
      id: 'personal-ranking-table',
      rows,
      commons,
      votesCount: 21,
      onDownloadData: () => {}
    })

    expect(ranks(container)).toEqual(['1', '2', '3'])

    const battles = container.querySelectorAll('thead th')[3].querySelector('button')!

    await fireEvent.click(battles)
    expect(ranks(container)).toEqual(['3', '1', '2'])

    await fireEvent.click(battles)
    expect(ranks(container)).toEqual(['2', '1', '3'])

    await fireEvent.click(battles)
    expect(ranks(container)).toEqual(['1', '2', '3'])
    expect(container.querySelectorAll('thead th')[2]).toHaveAttribute('aria-sort', 'descending')
  })
})
