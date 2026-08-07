<script lang="ts">
  import { getAuthContext } from '$lib/auth.svelte'
  import { m } from '$lib/i18n/messages'
  import { noop } from '$lib/utils/commons'
  import { canRecord, useVoiceRecorder } from '$lib/voice.svelte'
  import type { Attachment } from 'svelte/attachments'
  import { Button } from './dsfr'

  export type TextAreaProps = {
    id: string
    label: string
    value: string
    hideLabel?: boolean
    submitBtn?: boolean
    /** Offer a microphone. Off by default: the vote annotation box shares this
     * component and dictating a comment is not what it is for. */
    mic?: boolean
    /** Recordings whose transcription is still in the box, handed to the API on
     * send so the audio can be compared with what the user actually sent. */
    recordingIds?: string[]
    /** Wraps recording in the terms gate. A voice is captured here, which is a
     * heavier consent than sending text. */
    gate?: (action: () => unknown) => unknown
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
    mic = false,
    recordingIds = $bindable([]),
    gate = (action: () => unknown) => action(),
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

  const auth = getAuthContext()
  const showMic = $derived(mic && !!auth.config?.voice_enabled && canRecord())

  const recorder = useVoiceRecorder({
    maxSeconds: auth.config?.voice_max_seconds ?? 60,
    onText: (text, recordingId) => {
      value = value ? `${value.trimEnd()} ${text}` : text
      if (recordingId) recordingIds = [...recordingIds, recordingId]
      el?.focus()
      el?.setSelectionRange(value.length, value.length)
    },
    onError: (key) => {
      error = key === 'voice.denied' ? m['voice.denied']() : m['voice.failed']()
    }
  })

  const recording = $derived(recorder.recording)

  const maxSeconds = $derived(auth.config?.voice_max_seconds ?? 60)
  const elapsed = $derived(recorder.seconds + '/' + maxSeconds + 's')

  function toggleRecording() {
    // Recording and the error state both paint the box red and both speak into
    // the same live region, so an old error clears before one starts and the
    // two are never on at once.
    if (!recorder.recording) error = undefined
    gate(() => recorder.toggle())
  }
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
        'fr-input cg-border bg-white! text-sm! md:text-base md:min-h-10! rounded-b-none! border-solid!',
        { 'cl-recording': recording }
      ]}
      {...nativeTextAreaProps}
      aria-describedby="messages-{id}"
      {onkeydown}
      onblur={() => onBlur?.(value)}
      {@attach updateAuto}
      {@attach updateRows}
      onfocus={onFocus}
    ></textarea>
    {#if recording}
      <p class="cl-recording-badge right-3 top-3 gap-2 text-sm absolute flex items-center">
        <span class="cl-recording-dot"></span>
        <span>{elapsed}</span>
      </p>
    {/if}
    {#if showMic}
      <Button
        icon={recording ? 'stop-circle-line' : 'mic-line'}
        iconOnly
        {size}
        variant="secondary"
        disabled={recorder.transcribing}
        text={recording ? m['voice.stop']() : m['voice.start']()}
        onclick={toggleRecording}
        class={['bottom-3 absolute', submitBtn ? 'right-14' : 'right-3']}
      />
    {/if}
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
    {:else if recording}
      <p class="fr-message">{m['voice.recording']()}</p>
    {:else if recorder.transcribing}
      <p class="fr-message">{m['voice.transcribing']()}</p>
    {/if}
  </div>
  {#if showMic && auth.config?.voice_stores_audio}
    <p class="fr-hint-text">{m['voice.storageNotice']()}</p>
  {/if}
</div>

<style lang="postcss">
  .fr-input {
    --border-plain-grey: var(--blue-france-main-525);
  }

  /* Marianne red, not the DSFR error red: the error state already owns that
     colour and this box can be recording without anything being wrong. */
  .cl-recording {
    --border-plain-grey: var(--red-marianne-425-625);
    background-color: var(--red-marianne-975-75) !important;
  }

  .cl-recording-badge {
    color: var(--red-marianne-425-625);
  }

  .cl-recording-dot {
    width: 0.625rem;
    height: 0.625rem;
    border-radius: 50%;
    background-color: var(--red-marianne-425-625);
    animation: cl-recording-pulse 1.2s ease-in-out infinite;
  }

  @keyframes cl-recording-pulse {
    50% {
      opacity: 0.2;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .cl-recording-dot {
      animation: none;
    }
  }
</style>
