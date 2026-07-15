<script lang="ts">
  import { m } from '$lib/i18n/messages'
  import { noop } from '$lib/utils/commons'
  import type { Attachment } from 'svelte/attachments'
  import { Button } from './dsfr'

  export type TextAreaProps = {
    id: string
    label: string
    value: string
    hideLabel?: boolean
    submitBtn?: boolean
    submitDisabled?: boolean
    size?: 'sm' | 'md'
    maxRows?: number
    lineHeightPx?: number
    error?: string
    autofocus?: boolean
    autoscroll?: boolean
    el?: HTMLTextAreaElement
    class?: string
    onSubmit?: (value: string) => void
    onSubmitBlocked?: () => void
    onBlur?: (value: string) => void
    onFocus?: () => void
  } & Partial<Pick<HTMLTextAreaElement, 'disabled' | 'placeholder' | 'rows'>>

  let {
    id,
    label,
    value = $bindable(),
    submitBtn = false,
    submitDisabled = false,
    size = 'sm',
    hideLabel = false,
    rows = 1,
    maxRows = 4,
    lineHeightPx = 16 * 1.5,
    error = $bindable(),
    autofocus = false,
    autoscroll = false,
    el = $bindable(),
    class: classNames = '',
    onSubmit = noop,
    onSubmitBlocked = noop,
    onBlur = noop,
    onFocus = noop,
    ...nativeTextAreaProps
  }: TextAreaProps = $props()

  const updateRows: Attachment<HTMLTextAreaElement> = (el) => {
    if (rows >= maxRows) return

    const scrollOffset = el.scrollHeight - el.clientHeight
    if (value && scrollOffset > 0) {
      rows = Math.min(Math.ceil((scrollOffset + rows * lineHeightPx) / lineHeightPx), maxRows)
    }
  }

  const updateAuto: Attachment<HTMLTextAreaElement> = (el) => {
    if (autofocus) el.focus()
    if (autoscroll) el.scrollTo(0, el.scrollHeight)
  }

  const onkeydown = (e: KeyboardEvent) => {
    error = undefined
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!submitDisabled) {
        onSubmit(value)
      } else {
        onSubmitBlocked()
      }
    }
  }

  const roundedClass = $derived(
    size === 'sm' ? 'rounded-t-sm! rounded-s-sm!' : 'rounded-t-xl! rounded-s-xl!'
  )
</script>

<div class={['fr-input-group', classNames, { 'fr-input-group--error': !!error }]}>
  <label for={id} class={['fr-label', { 'hidden!': hideLabel }]}>{label}</label>
  <div class="relative">
    <textarea
      {id}
      data-testid="textbox"
      bind:value
      bind:this={el}
      {rows}
      class={[
        roundedClass,
        'fr-input cg-border bg-white! text-sm! md:text-base md:min-h-10! rounded-b-none! border-solid!'
      ]}
      {...nativeTextAreaProps}
      aria-describedby="messages-{id}"
      {onkeydown}
      onblur={() => onBlur?.(value)}
      {@attach updateAuto}
      {@attach updateRows}
      onfocus={onFocus}
    ></textarea>
    {#if submitBtn}
      <Button
        icon="arrow-up-line"
        iconOnly
        {size}
        aria-disabled={submitDisabled}
        text={m['words.send']()}
        onclick={() => (submitDisabled ? onSubmitBlocked() : onSubmit(value))}
        class="right-3 bottom-3 absolute"
      />
    {/if}
  </div>
  <div class="fr-messages-group" id="messages-{id}" aria-live="polite">
    {#if error}
      <p class="fr-message fr-message--error" id="messages-{id}-error">{error}</p>
    {/if}
  </div>
</div>

<style lang="postcss">
  .fr-input {
    --border-plain-grey: var(--blue-france-main-525);
  }
</style>
