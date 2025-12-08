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
  <label for={id} class={['fr-label', { 'hidden!': hideLabel }]}>{label}</label>
  <textarea
    {id}
    data-testid="textbox"
    bind:value
    bind:this={el}
    {rows}
    class="fr-input cg-border rounded-t-md! bg-white! md:min-h-10! rounded-b-none! border-solid!"
    {...nativeTextAreaProps}
    {onkeypress}
    {@attach updateAuto}
    {@attach updateRows}
  ></textarea>
</div>

<style lang="postcss">
  .fr-input {
    --border-plain-grey: var(--blue-france-main-525);
  }
</style>
