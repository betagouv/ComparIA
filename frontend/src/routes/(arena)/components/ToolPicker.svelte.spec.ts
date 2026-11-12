import { fireEvent, render, screen } from '@testing-library/svelte'
import { m } from '$lib/i18n/messages'
import { describe, expect, it, vi } from 'vitest'
import ToolPicker from './ToolPicker.svelte'

vi.mock('$env/dynamic/public', () => ({ env: {} }))

// jsdom has no Web Animations API, which the dropdown's fade-in needs.
Element.prototype.animate ??= vi.fn(() => ({
  cancel: vi.fn(),
  finished: Promise.resolve()
})) as unknown as Element['animate']

const tools = [
  { key: 'web_search', label: 'Recherche web', description: 'Chercher sur le web' },
  { key: 'datagouv', label: 'Données publiques', description: 'Jeux de données publics' }
]

function trigger(container: HTMLElement) {
  return container.querySelector<HTMLButtonElement>('button[aria-controls="dropdown-tools"]')!
}

describe('ToolPicker', () => {
  it('shows the number of selected tools on the trigger', () => {
    const { container } = render(ToolPicker, { props: { tools, selected: ['web_search'] } })

    expect(trigger(container).textContent).toMatch(/Outils\s*1/)
  })

  it('offers one toggle per tool, checked when selected', () => {
    const { container } = render(ToolPicker, { props: { tools, selected: ['datagouv'] } })

    const toggles = container.querySelectorAll<HTMLInputElement>('#dropdown-tools input')
    expect([...toggles].map((input) => input.id)).toEqual([
      'tool-web_search-dropdown',
      'tool-datagouv-dropdown'
    ])
    expect([...toggles].map((input) => input.checked)).toEqual([false, true])
  })

  it('applies the toggled tools when the visitor adds them', async () => {
    const { container } = render(ToolPicker, { props: { tools, selected: [] } })

    await fireEvent.click(container.querySelector('#tool-web_search-dropdown')!)
    await fireEvent.click(
      screen.getAllByRole('button', { name: m['arenaHome.tools.add'](), hidden: true })[0]
    )

    expect(trigger(container).textContent).toMatch(/Outils\s*1/)
  })

  it('clears the selection in one click', async () => {
    const { container } = render(ToolPicker, {
      props: { tools, selected: ['web_search', 'datagouv'] }
    })

    await fireEvent.click(screen.getByText('Tout désélectionner'))
    expect(trigger(container).textContent).toMatch(/Outils\s*0/)
  })

  it('states that both models are offered the tools and stay free to use them', () => {
    render(ToolPicker, { props: { tools, selected: [] } })

    expect(screen.getByText(/libres de les utiliser ou non/)).toBeTruthy()
  })

  it('shows the tools a mode forces as always on, with nothing to change', () => {
    const { container } = render(ToolPicker, {
      props: { tools: [tools[0]], selected: ['web_search'], locked: true }
    })

    expect(screen.getByText('Recherche web')).toBeInTheDocument()
    expect(screen.getByText(/Toujours actif dans ce mode/)).toBeInTheDocument()
    expect(container.querySelector('button')).toBeNull()
    expect(container.querySelector('input')).toBeNull()
  })

  it('offers only the tools it is given', () => {
    const { container } = render(ToolPicker, { props: { tools: [tools[1]], selected: [] } })

    expect(container.querySelector('#tool-web_search-dropdown')).toBeNull()
    expect(container.querySelector('#tool-datagouv-dropdown')).not.toBeNull()
  })

  it('renders nothing when no tool is on offer', () => {
    const { container } = render(ToolPicker, { props: { tools: [], selected: [] } })

    expect(container.textContent?.trim()).toBe('')
  })
})
