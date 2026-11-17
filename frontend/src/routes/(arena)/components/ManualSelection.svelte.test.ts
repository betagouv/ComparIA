import { fireEvent, render } from '@testing-library/svelte'
import { flushSync } from 'svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ViewPrompt from './ViewPrompt.svelte'

const toast = vi.hoisted(() => vi.fn())
vi.mock('$lib/helpers/useToast.svelte', () => ({ useToast: toast }))

const model = (id: string, human_id: string, name: string, lab: string) => ({
  id,
  human_id,
  name,
  status: 'enabled',
  custom_selectable: true,
  lab: { id: lab, name: lab, logo: 'x' },
  badges: {},
  search: [human_id, name, lab].join(' ').toLowerCase()
})

vi.mock('$lib/models', () => ({
  getModelsContext: () => ({
    models: [
      model('gemma', 'gemma-4-31b', 'Gemma 4 31B', 'Google'),
      model('mistral', 'mistral-small-4', 'Mistral Small 4', 'Mistral AI'),
      model('qwen', 'qwen-3-8', 'Qwen 3.8 27B', 'Alibaba')
    ]
  })
}))

// Element.animate is missing from jsdom and the model picker fades in with it.
Element.prototype.animate ??= vi.fn(() => ({
  cancel: vi.fn(),
  finished: Promise.resolve()
})) as unknown as Element['animate']

/**
 * A real click lets Svelte re-render between the click and the `change` event
 * it triggers, so a radio the click handler removes never fires `change`. A
 * script-driven click is synchronous and hides that, so flush the DOM at the
 * point a browser would.
 */
async function realClick(el: HTMLElement) {
  const flushLikeABrowser = () => flushSync()
  document.addEventListener('click', flushLikeABrowser, { once: true })
  el.click()
  await Promise.resolve()
}

const props = { loading: false, suggestions: [] }

describe('manual model selection', () => {
  beforeEach(() => {
    localStorage.clear()
    toast.mockClear()
    vi.stubGlobal('dsfr', () => ({ modal: { conceal: vi.fn() } }))
  })

  it.each([
    ['random', /Aléatoire/],
    ['small-models', /Modèles frugaux|Frugal/],
    ['big-vs-small', /Petit contre grand|Grand|Big/]
  ])('uses the chosen models when manual selection is picked from %s', async (start) => {
    localStorage.setItem('mode', start)
    const onPrompt = vi.fn()
    const view = render(ViewPrompt, { ...props, onPrompt })

    await realClick(view.getByRole('radio', { name: /Sélection manuelle/, hidden: true }))
    await fireEvent.click(view.getByLabelText(/Gemma 4 31B/, { selector: 'input' }))
    await fireEvent.click(view.getByLabelText(/Mistral Small 4/, { selector: 'input' }))

    await fireEvent.input(view.getByRole('textbox'), { target: { value: 'Bonjour' } })
    await fireEvent.click(view.getByRole('button', { name: 'Envoyer' }))

    expect(onPrompt).toHaveBeenCalledOnce()
    expect(onPrompt).toHaveBeenCalledWith(
      expect.objectContaining({ mode: 'custom', custom_models_selection: ['gemma', 'mistral'] })
    )
  })

  it('keeps manual mode when one model is chosen and validated', async () => {
    const onPrompt = vi.fn()
    const view = render(ViewPrompt, { ...props, onPrompt })

    await realClick(view.getByRole('radio', { name: /Sélection manuelle/, hidden: true }))
    await fireEvent.click(view.getByLabelText(/Qwen 3.8 27B/, { selector: 'input' }))

    await fireEvent.input(view.getByRole('textbox'), { target: { value: 'Bonjour' } })
    await fireEvent.click(view.getByRole('button', { name: 'Envoyer' }))

    expect(onPrompt).toHaveBeenCalledWith(
      expect.objectContaining({ mode: 'custom', custom_models_selection: ['qwen'] })
    )
  })
})
