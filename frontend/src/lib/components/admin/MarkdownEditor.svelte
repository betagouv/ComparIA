<script lang="ts">
  import { onMount } from 'svelte'
  import 'tiny-markdown-editor/dist/tiny-mde.css'

  import type { CommandBar, Editor } from 'tiny-markdown-editor'

  type MarkdownChangeEvent = { content: string }
  type MarkdownCommand =
    | string
    | {
        name: string
        title: string
        innerHTML?: string
      }

  let {
    id,
    label,
    labelClass,
    value = $bindable(''),
    help,
    rows = 6,
    maxlength,
    required = false,
    mode = 'block',
    allowLinks = true
  }: {
    id: string
    label: string
    labelClass?: string
    value?: string
    help?: string
    rows?: number
    maxlength?: number
    required?: boolean
    mode?: 'inline' | 'block'
    allowLinks?: boolean
  } = $props()

  let textarea = $state<HTMLTextAreaElement>()
  let toolbar = $state<HTMLDivElement>()
  let editor: Editor | undefined
  let commandBar: CommandBar | undefined
  let updatingFromEditor = false

  const inlineCommands: MarkdownCommand[] = [
    { name: 'bold', title: 'Gras' },
    { name: 'italic', title: 'Italique' }
  ]

  function getCommands(): MarkdownCommand[] {
    const commands = [...inlineCommands]
    if (allowLinks) {
      commands.push({ name: 'insertLink', title: 'Insérer un lien' })
    }
    if (mode === 'block') {
      commands.push('|', { name: 'h2', title: 'Titre' }, { name: 'ul', title: 'Liste à puces' })
    }
    return commands
  }

  function makeToolbarAccessible() {
    if (!toolbar || !commandBar?.e) return
    commandBar.e.setAttribute('role', 'toolbar')
    commandBar.e.setAttribute('aria-label', `Mise en forme Markdown — ${label}`)

    for (const button of Object.values(commandBar.buttons)) {
      button.setAttribute('role', 'button')
      button.setAttribute('tabindex', '0')
      button.setAttribute('aria-label', button.title)
      button.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter' && event.key !== ' ') return
        event.preventDefault()
        button.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))
      })
    }
  }

  onMount(() => {
    let disposed = false

    async function initialiseEditor() {
      if (!textarea || !toolbar) return
      const TinyMDE = await import('tiny-markdown-editor')
      if (disposed) return
      editor = new TinyMDE.Editor({ textarea })
      commandBar = new TinyMDE.CommandBar({
        element: toolbar,
        editor,
        commands: getCommands()
      })

      if (editor.e) {
        editor.e.id = `${id}-editor`
        editor.e.setAttribute('role', 'textbox')
        editor.e.setAttribute('aria-multiline', 'true')
        editor.e.setAttribute('aria-labelledby', `${id}-label`)
        if (help) editor.e.setAttribute('aria-describedby', `${id}-help`)
        if (required) editor.e.setAttribute('aria-required', 'true')
        editor.e.style.minHeight = `${Math.max(rows, 2) * 1.5}rem`
      }

      makeToolbarAccessible()
      editor.addEventListener('change', (event: MarkdownChangeEvent) => {
        updatingFromEditor = true
        value = maxlength ? event.content.slice(0, maxlength) : event.content
        if (value !== event.content) editor?.setContent(value)
        queueMicrotask(() => (updatingFromEditor = false))
      })
    }

    void initialiseEditor()

    return () => {
      disposed = true
      commandBar?.e?.remove()
      editor?.e?.remove()
      textarea?.style.removeProperty('display')
      editor = undefined
      commandBar = undefined
    }
  })

  $effect(() => {
    if (!editor || updatingFromEditor || editor.getContent() === value) return
    editor.setContent(value)
  })
</script>

<div class="fr-input-group">
  <label id={`${id}-label`} class={['fr-label', labelClass]} for={`${id}-editor`}>
    {label}
    {#if help}<span id={`${id}-help`} class="fr-hint-text">{help}</span>{/if}
  </label>
  <div bind:this={toolbar} class="markdown-toolbar fr-mt-1v"></div>
  <div class="markdown-editor">
    <textarea
      bind:this={textarea}
      bind:value
      {id}
      class="fr-input"
      aria-labelledby={`${id}-label`}
      aria-describedby={help ? `${id}-help` : undefined}
      {rows}
      {maxlength}
      {required}
    ></textarea>
  </div>
</div>

<style>
  :global(.markdown-toolbar .TMCommandBar) {
    border-radius: 0.25rem 0.25rem 0 0;
  }

  :global(.markdown-toolbar .TMCommandButton:focus-visible) {
    outline: 2px solid var(--border-active-blue-france);
    outline-offset: 2px;
  }

  :global(.markdown-editor .TinyMDE) {
    overflow-y: auto;
    box-sizing: border-box;
    width: 100%;
    padding: 0.5rem 1rem;
    border: 0;
    border-bottom: 2px solid var(--border-plain-grey);
    border-radius: 0.25rem 0.25rem 0 0;
    background-color: var(--background-contrast-grey);
    color: var(--text-default-grey);
    font: inherit;
  }

  :global(.markdown-editor .TinyMDE:focus) {
    outline: 2px solid var(--border-active-blue-france);
    outline-offset: 2px;
  }
</style>
