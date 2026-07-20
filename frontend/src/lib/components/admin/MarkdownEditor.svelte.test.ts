import { render, waitFor } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import MarkdownEditor from './MarkdownEditor.svelte'

describe('MarkdownEditor', () => {
  it('loads the TinyMDE editor and its Markdown commands', async () => {
    const { getByRole } = render(MarkdownEditor, {
      id: 'editor',
      label: 'Contenu',
      value: 'Texte important'
    })

    await waitFor(() => {
      expect(getByRole('textbox', { name: 'Contenu' }).textContent).toContain('Texte important')
    })
    expect(getByRole('toolbar', { name: 'Mise en forme Markdown — Contenu' })).toBeTruthy()
    expect(getByRole('button', { name: /Gras/ })).toBeTruthy()
    expect(getByRole('button', { name: /Insérer un lien/ })).toBeTruthy()
    expect(getByRole('button', { name: /Titre/ })).toBeTruthy()
  })

  it('offers fewer actions for inline button labels', async () => {
    const { getByRole, queryByRole } = render(MarkdownEditor, {
      id: 'inline-editor',
      label: 'Bouton',
      mode: 'inline',
      allowLinks: false
    })

    await waitFor(() => expect(getByRole('button', { name: /Gras/ })).toBeTruthy())
    expect(queryByRole('button', { name: /Insérer un lien/ })).toBeNull()
    expect(queryByRole('button', { name: /Titre/ })).toBeNull()
  })
})
