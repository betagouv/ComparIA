/**
 * The ranking charts need vote data the local stack does not have, so they are
 * covered here rather than in the browser suite. An SVG with no role and no
 * title is a blank rectangle to a screen reader, which is what both of these
 * were before the audit of 2026-08-13.
 */
import { render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import { expectAccessible } from '$lib/testing/a11y'
import WinHistogram from './WinHistogram.svelte'

describe('WinHistogram', () => {
  const data = [
    { x: 'Alpha', y: 0.62 },
    { x: 'Beta', y: 0.55 }
  ]

  it('names itself so it is not an anonymous graphic', async () => {
    const { container } = render(WinHistogram, {
      id: 'histogram-winrate',
      title: '10 premiers modèles selon le taux de victoire',
      data,
      minMaxY: [0, 1] as [number, number]
    })

    const svg = container.querySelector('svg')!
    expect(svg.getAttribute('role')).toBe('img')

    const titleId = svg.getAttribute('aria-labelledby')!
    const title = container.querySelector(`#${titleId}`)!
    expect(title.tagName.toLowerCase()).toBe('title')
    expect(title.textContent).toContain('taux de victoire')

    await expectAccessible(container)
  })

  it('gives the two histograms on the methodology tab separate ids', () => {
    const { container: a } = render(WinHistogram, {
      id: 'histogram-winrate',
      title: 'Taux de victoire',
      data,
      minMaxY: [0, 1] as [number, number]
    })
    const { container: b } = render(WinHistogram, {
      id: 'histogram-elo',
      title: 'Bradley-Terry',
      data,
      minMaxY: [0, 1] as [number, number]
    })

    const ids = [a, b].map((c) => c.querySelector('svg')!.getAttribute('aria-labelledby'))
    expect(new Set(ids).size).toBe(2)
  })
})
