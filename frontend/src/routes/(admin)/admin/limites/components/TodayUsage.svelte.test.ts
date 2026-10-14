import { render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import TodayUsage from './TodayUsage.svelte'

const day = { input_chars: 0, output_chars: 0, resets_in: 3600 }
const usage = [
  {
    ...day,
    llm_id: 'full',
    name: 'GPT 5.5',
    estimated_usd: 21.5,
    cap_usd: 20,
    resting: true,
    answers: 40,
    cached_answers: 10
  },
  {
    ...day,
    llm_id: 'open',
    name: 'Gemma 4',
    estimated_usd: 0.42,
    cap_usd: null,
    resting: false,
    answers: 0,
    cached_answers: 0
  }
]

function row(view: ReturnType<typeof render>, name: string) {
  return view.getByRole('link', { name }).closest('tr')!
}

describe('TodayUsage', () => {
  it("lists each model's spend against its cap, with the ones at rest marked", () => {
    const view = render(TodayUsage, { usage })

    expect(row(view, 'GPT 5.5')).toHaveTextContent(/GPT 5.5\s*Au repos\s*21,50\s*\$\s*20,00\s*\$/)
    expect(row(view, 'GPT 5.5')).toHaveTextContent('25 % de 40')
    expect(row(view, 'Gemma 4')).toHaveTextContent('Aucun')
    expect(row(view, 'Gemma 4')).toHaveTextContent('Aucune réponse')
    expect(row(view, 'Gemma 4')).not.toHaveTextContent('Au repos')
    expect(view.queryByRole('columnheader', { name: /Proposé/ })).toBeNull()
  })

  it('shows the caps the calibration proposes next to each model', () => {
    const proposals = [{ llm_id: 'full', value: 30, days: 6, percentile: 95, highest: 21.5 }]
    const view = render(TodayUsage, { usage, proposals })

    expect(view.getByRole('columnheader', { name: /Proposé/ })).toBeInTheDocument()
    expect(row(view, 'GPT 5.5')).toHaveTextContent(
      /30,00\s*\$ : 95e centile de 6 jours, plus la moitié\. Au plus 21,50\s*\$ en un jour\./
    )
  })

  it('says so when the spend cannot be read', () => {
    const view = render(TodayUsage, { usage: null })

    expect(view.getByText("Les dépenses du jour n'ont pas pu être lues.")).toBeInTheDocument()
  })
})
