import { render, screen } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import type { PageProps } from './$types'
import Page from './+page.svelte'

const llm = (id: string, price_in: number, price_out: number) => ({
  id,
  human_id: id,
  name: id,
  status: 'enabled',
  price_in,
  price_out,
  release_date: '2026-01-01',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z'
})

const day = (llm_id: string, cap_usd: number | null, counted: boolean) => ({
  llm_id,
  name: llm_id,
  input_chars: 0,
  output_chars: 0,
  estimated_usd: 0,
  cap_usd,
  full: false,
  resets_in: 3600,
  answers: 0,
  cached_answers: 0,
  counted
})

function row(name: string) {
  return screen.getByRole('link', { name }).closest('tr')!
}

describe('LLM list', () => {
  it('says in the "Aujourd’hui" column that a cap on a model without a price has no effect', () => {
    render(Page, {
      data: {
        llms: [llm('apertus-70b', 0, 0), llm('gpt-5.5', 4.3, 26)],
        data: { models: [] },
        usage: [day('apertus-70b', 5, false), day('gpt-5.5', 20, true)]
      }
    } as unknown as PageProps)

    expect(row('apertus-70b')).toHaveTextContent(
      'Sans prix, ce modèle n’est pas compté : son plafond n’a aucun effet.'
    )
    expect(row('gpt-5.5')).not.toHaveTextContent(/Sans prix/)
  })
})
