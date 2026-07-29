import { fireEvent, render, screen } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import ToolPicker from './ToolPicker.svelte'

vi.mock('$env/dynamic/public', () => ({ env: {} }))

const tools = [
  { key: 'web_search', label: 'Recherche web', description: 'Chercher sur le web' },
  { key: 'datagouv', label: 'Données publiques', description: 'Jeux de données publics' }
]

describe('ToolPicker', () => {
  it('starts with nothing selected', () => {
    const { container } = render(ToolPicker, { props: { tools, selected: [] } })

    expect(screen.getByText('Aucun outil')).toBeTruthy()
    const toolTags = container.querySelectorAll<HTMLButtonElement>('button[aria-pressed]')
    expect(toolTags.length).toBe(tools.length)
    for (const tag of toolTags) expect(tag.getAttribute('aria-pressed')).toBe('false')
  })

  it('renders tools as pressable pills and toggles their selection', async () => {
    const { container } = render(ToolPicker, { props: { tools, selected: [] } })
    const webSearch = container.querySelector<HTMLButtonElement>(
      'button[aria-describedby="tool-web_search-description"]'
    )

    expect(webSearch?.classList.contains('fr-tag')).toBe(true)
    expect(webSearch?.getAttribute('aria-pressed')).toBe('false')

    await fireEvent.click(webSearch!)
    expect(webSearch?.getAttribute('aria-pressed')).toBe('true')

    await fireEvent.click(webSearch!)
    expect(webSearch?.getAttribute('aria-pressed')).toBe('false')
  })

  it('shows the tools title only once in the modal', () => {
    render(ToolPicker, { props: { tools, selected: [] } })

    expect(screen.getAllByText('Outils')).toHaveLength(1)
  })

  it('shows the number of selected tools on the trigger', () => {
    const { container } = render(ToolPicker, { props: { tools, selected: ['web_search'] } })

    expect(container.querySelector('button')?.textContent).toContain('Outils (1)')
  })

  it('keeps the same compact label with multiple selected tools', () => {
    const { container } = render(ToolPicker, {
      props: { tools, selected: ['web_search', 'datagouv'] }
    })

    expect(container.querySelector('button')?.textContent).toContain('Outils (2)')
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
