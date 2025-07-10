<script lang="ts">
  import { noop } from '$lib/utils/commons'
  import type { Attachment } from 'svelte/attachments'

  export type TextAreaProps = {
    id: string
    label: string
    value: string
    hideLabel?: boolean
    maxRows?: number
    lineHeightPx?: number
    autofocus?: boolean
    autoscroll?: boolean
    el?: HTMLTextAreaElement
    class?: string
    onSubmit?: (value: string) => void
  } & Partial<Pick<HTMLTextAreaElement, 'disabled' | 'placeholder' | 'rows'>>

  let {
    id,
    label,
    value = $bindable(),
    hideLabel = false,
    rows = 1,
    maxRows = 4,
    lineHeightPx = 16 * 1.5,
    autofocus = false,
    autoscroll = false,
    el = $bindable(),
    class: classNames = '',
    onSubmit = noop,
    ...nativeTextAreaProps
  }: TextAreaProps = $props()

  const updateRows: Attachment<HTMLTextAreaElement> = (el) => {
    if (rows >= maxRows) return

    const scrollOffset = el.scrollHeight - el.clientHeight
    if (value && scrollOffset > 0) {
      rows = Math.min(Math.ceil(scrollOffset / lineHeightPx), maxRows)
    }
  }

  const updateAuto: Attachment<HTMLTextAreaElement> = (el) => {
    if (autofocus) el.focus()
    if (autoscroll) el.scrollTo(0, el.scrollHeight)
  }

  const onkeypress = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      onSubmit(value)
    }
  }
</script>

<div class="fr-input-group {classNames}">
  <label class="fr-label" for={id} class:hidden={hideLabel}>{label}</label>
  <textarea
    {id}
    data-testid="textbox"
    bind:value
    bind:this={el}
    {rows}
    class="fr-input scroll-hide"
    {...nativeTextAreaProps}
    {onkeypress}
    {@attach updateAuto}
    {@attach updateRows}
  ></textarea>
</div>

<!--  -->
<style>
  textarea.fr-input {
    background-color: var(--background-default-grey);
    border-radius: 0.5em 0.5em 0 0;
    border: 1px solid var(--border-default-grey);
    box-shadow: inset 0 -2px 0 0 var(--blue-france-main-525);
    /* outline: none !important;
    outline-offset: 0 !important; */
  }

  @media (min-width: 48em) {
    textarea.fr-input {
      min-height: 2.5rem !important;
    }
  }
</style>
