import { render, screen } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import ToolPicker from './ToolPicker.svelte'

vi.mock('$env/dynamic/public', () => ({ env: {} }))

const tools = [
  { key: 'web_search', label: 'Recherche web', description: 'Chercher sur le web' },
  { key: 'datagouv', label: 'Données publiques', description: 'Jeux de données publics' }
]

describe('ToolPicker', () => {
  it('starts with nothing selected', () => {
    // Queried from the DOM rather than by role: the options live inside a
    // <dialog>, which exposes no accessible roles until it is opened.
    const { container } = render(ToolPicker, { props: { tools, selected: [] } })

    expect(screen.getByText('Aucun outil')).toBeTruthy()
    const boxes = container.querySelectorAll<HTMLInputElement>('input[type="checkbox"]')
    expect(boxes.length).toBe(tools.length)
    for (const box of boxes) expect(box.checked).toBe(false)
  })

  it('names the single selected tool on the trigger', () => {
    const { container } = render(ToolPicker, { props: { tools, selected: ['web_search'] } })

    expect(container.querySelector('button')?.textContent).toContain('Recherche web')
  })

  it('counts the selection past one tool', () => {
    render(ToolPicker, { props: { tools, selected: ['web_search', 'datagouv'] } })

    expect(screen.getByText('2 outils')).toBeTruthy()
  })

  it('states that both models are offered the tools and stay free to use them', () => {
    render(ToolPicker, { props: { tools, selected: [] } })

    expect(screen.getByText(/libres de les utiliser ou non/)).toBeTruthy()
  })

  it('renders nothing when the instance has no tool configured', () => {
    const { container } = render(ToolPicker, { props: { tools: [], selected: [] } })

    expect(container.textContent?.trim()).toBe('')
  })
})
