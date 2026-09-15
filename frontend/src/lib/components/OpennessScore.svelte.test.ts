import { fireEvent, render, screen } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import type { BotModel } from '$lib/models'
import OpennessScore from './OpennessScore.svelte'

const model = {
  id: 'model-1',
  sovereignty_score: 4,
  license: {
    reuse: true,
    commercial_use: true
  },
  public_weights: true,
  public_training_data: false,
  public_training_code: false,
  eu_hostable: true
} as BotModel

describe('OpennessScore', () => {
  it('reveals the openness criteria when activated', async () => {
    render(OpennessScore, { model, detailed: true })

    const trigger = screen.getByRole('button', { name: 'Niveau d’ouverture : 4/6' })
    expect(trigger).toHaveAttribute('aria-expanded', 'false')

    await fireEvent.click(trigger)

    expect(trigger).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('tooltip')).toHaveTextContent('Jeux de données d’entraînement')
    expect(screen.getByRole('tooltip')).toHaveTextContent('Hébergeable dans l’UE')
  })
})
