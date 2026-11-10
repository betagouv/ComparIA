import { fireEvent, render, screen, within } from '@testing-library/svelte'
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

    expect(container.querySelector('button')?.textContent).toContain('Outils 0')
    const toolTags = container.querySelectorAll<HTMLButtonElement>(
      '#dropdown-tools input[type="checkbox"]'
    )
    expect(toolTags.length).toBe(tools.length)
    for (const tag of toolTags) expect(tag).not.toBeChecked()
  })

  it('renders tools as toggle and toggles their selection', async () => {
    const { container } = render(ToolPicker, { props: { tools, selected: [] } })
    const webSearch = container.querySelector<HTMLInputElement>('#tool-web_search-dropdown')

    expect(webSearch).not.toBeChecked()

    await fireEvent.click(webSearch!)
    expect(webSearch).toBeChecked()

    await fireEvent.click(webSearch!)
    expect(webSearch).not.toBeChecked()
  })

  it('shows each description next to its tool', () => {
    render(ToolPicker, { props: { tools, selected: [] } })

    expect(screen.getAllByText('Chercher sur le web')).toHaveLength(2)
  })

  it('clears the selection in one click', async () => {
    const { container } = render(ToolPicker, {
      props: { tools, selected: ['web_search', 'datagouv'] }
    })
    const dialog = within(container.ownerDocument.getElementById('fr-modal-tools')!)
    expect(dialog.getAllByRole('checkbox', { checked: true, hidden: true })).toHaveLength(2)
    await fireEvent.click(screen.getByText('Tout désélectionner'))
    expect(dialog.getAllByRole('checkbox', { checked: false, hidden: true })).toHaveLength(2)
  })

  it('shows the number of selected tools on the trigger', () => {
    const { container } = render(ToolPicker, { props: { tools, selected: ['web_search'] } })

    expect(container.querySelector('button')?.textContent).toContain('Outils 1')
  })

  it('keeps the same compact label with multiple selected tools', () => {
    const { container } = render(ToolPicker, {
      props: { tools, selected: ['web_search', 'datagouv'] }
    })

    expect(container.querySelector('button')?.textContent).toContain('Outils 2')
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
