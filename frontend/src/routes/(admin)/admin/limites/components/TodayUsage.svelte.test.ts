import { render, screen } from '@testing-library/svelte'
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
    full: true,
    answers: 40,
    cached_answers: 10
  },
  {
    ...day,
    llm_id: 'open',
    name: 'Gemma 4',
    estimated_usd: 0.42,
    cap_usd: null,
    full: false,
    answers: 0,
    cached_answers: 0
  },
  {
    ...day,
    llm_id: 'idle',
    name: 'Llama 4 Scout',
    estimated_usd: 0,
    cap_usd: null,
    full: false,
    answers: 0,
    cached_answers: 0
  }
]

function row(name: string) {
  return screen.getByRole('link', { name }).closest('tr')!
}

describe('TodayUsage', () => {
  it("lists each model's spend against its cap, with the ones at rest marked", () => {
    const view = render(TodayUsage, { usage })

    expect(row('GPT 5.5')).toHaveTextContent(/GPT 5.5\s*Au repos\s*21,50\s*\$\s*20,00\s*\$/)
    expect(row('GPT 5.5')).toHaveTextContent('25 % de 40')
    expect(row('Gemma 4')).toHaveTextContent('Aucun')
    expect(row('Gemma 4')).toHaveTextContent('Aucune réponse')
    expect(row('Gemma 4')).not.toHaveTextContent('Au repos')
    expect(view.queryByRole('columnheader', { name: /Proposé/ })).toBeNull()
    // A model that cost nothing and has no cap is only counted.
    expect(view.queryByRole('link', { name: 'Llama 4 Scout' })).toBeNull()
    expect(
      view.getByText("1 autre modèle activé n'a rien coûté aujourd'hui et n'a pas de plafond.")
    ).toBeInTheDocument()
  })

  it('lists a model with nothing spent once a cap is proposed for it', () => {
    const proposals = [{ llm_id: 'idle', value: 5, days: 6, percentile: 95, highest: 3 }]
    const view = render(TodayUsage, { usage, proposals })

    expect(view.getByRole('link', { name: 'Llama 4 Scout' })).toBeInTheDocument()
  })

  it('shows the caps the calibration proposes next to each model', () => {
    const proposals = [{ llm_id: 'full', value: 30, days: 6, percentile: 95, highest: 21.5 }]
    const view = render(TodayUsage, { usage, proposals })

    expect(view.getByRole('columnheader', { name: /Proposé/ })).toBeInTheDocument()
    expect(row('GPT 5.5')).toHaveTextContent(/30,00\s*\$\s*au plus 21,50\s*\$ en un jour/)
    expect(
      view.getByText(
        "Plafond proposé : ce que chaque modèle coûteux n'a pas dépassé sur 95 % des 6 jours entiers lus, plus la moitié."
      )
    ).toBeInTheDocument()
  })

  it('warns that a proposed cap below what the model spent today rests it at once', () => {
    const proposals = [
      { llm_id: 'full', value: 30, days: 6, percentile: 95, highest: 21.5 },
      { llm_id: 'open', value: 0.3, days: 6, percentile: 95, highest: 0.2 }
    ]
    const view = render(TodayUsage, { usage, proposals })

    expect(row('Gemma 4')).toHaveTextContent(/le met au repos tout de suite, pour tout le monde/)
    expect(row('GPT 5.5')).not.toHaveTextContent(/au repos tout de suite/)
    view.unmount()
  })

  it('says so when the spend cannot be read', () => {
    const view = render(TodayUsage, { usage: null })

    expect(view.getByText("Les dépenses du jour n'ont pas pu être lues.")).toBeInTheDocument()
  })
})
