<script lang="ts">
  import { m } from '$lib/i18n/messages'
  import { teleport } from '$lib/helpers/attachments'
  import { noop } from '$lib/utils/commons'
  import type { VoiceInput } from '$lib/voice.svelte'
  import type { Attachment } from 'svelte/attachments'
  import { onDestroy } from 'svelte'
  import { Button } from './dsfr'

  export type TextAreaProps = {
    id: string
    label: string
    value: string
    hideLabel?: boolean
    submitBtn?: boolean
    /** Offer a microphone. Absent on the vote annotation box, which shares this
     * component and is not what dictation is for. */
    voice?: VoiceInput
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
    voice,
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

  let recording = $state(false)
  let transcribing = $state(false)
  let seconds = $state(0)
  let model = $state('')

  let recorder: MediaRecorder | null = null
  let timer: ReturnType<typeof setInterval> | null = null
  let modelTimer: ReturnType<typeof setTimeout> | null = null
  let startedAt = 0

  // The notice explains what happens to a recording, so it has no business
  // covering the box once one is under way.
  const showHint = $derived(!!voice?.notice && !recording && !transcribing)

  // Long enough to read, short enough that the box goes back to being a box.
  const MODEL_BAR_MS = 5000

  const showModel = $derived(!!model && !!value && !recording && !transcribing)
  // The vendor prefix is for the admin who edits the pool. On a chip beside the
  // microphone, "voxtral-mini-transcribe" is the part that says anything.
  const shortModel = $derived(model.slice(model.lastIndexOf('/') + 1))

  // The button that started the recording is the thing waiting on the provider,
  // so it spins rather than a line of text appearing under the box.
  const micIcon = $derived(
    recording ? 'stop-circle-line' : transcribing ? 'refresh-line' : 'mic-line'
  )

  const maxSeconds = $derived(voice?.maxSeconds ?? 60)
  const elapsed = $derived(seconds + '/' + maxSeconds + 's')

  function releaseTracks() {
    recorder?.stream.getTracks().forEach((track) => track.stop())
    recorder = null
  }

  async function transcribe(audio: Blob, durationMs: number) {
    transcribing = true
    try {
      const result = await voice?.transcribe(audio, durationMs)
      if (!result?.text) {
        error = m['voice.failed']()
        return
      }
      const { text } = result
      model = result.model
      if (modelTimer) clearTimeout(modelTimer)
      modelTimer = setTimeout(() => (model = ''), MODEL_BAR_MS)
      value = value ? `${value.trimEnd()} ${text}` : text
      el?.focus()
      el?.setSelectionRange(value.length, value.length)
    } catch (e) {
      console.error(e)
      error = m['voice.failed']()
    } finally {
      transcribing = false
    }
  }

  async function start() {
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (e) {
      console.error(e)
      error = m['voice.denied']()
      return
    }

    const chunks: Blob[] = []
    recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
    recorder.ondataavailable = (e) => chunks.push(e.data)
    recorder.onstop = () => {
      const durationMs = Date.now() - startedAt
      releaseTracks()
      transcribe(new Blob(chunks, { type: 'audio/webm' }), durationMs)
    }

    startedAt = Date.now()
    seconds = 0
    model = ''
    recording = true
    recorder.start()

    timer = setInterval(() => {
      seconds = Math.floor((Date.now() - startedAt) / 1000)
      // Stops itself rather than letting someone hold a paid endpoint open,
      // and keeps every recording clear of the provider's own cut-off.
      if (seconds >= maxSeconds) stop()
    }, 250)
  }

  function stop() {
    if (timer) clearInterval(timer)
    timer = null
    recording = false
    recorder?.stop()
  }

  // Sending the first prompt swaps this box for the one in the conversation
  // view, which can happen mid-recording. Without this the interval keeps
  // ticking and the browser goes on showing that the microphone is live.
  onDestroy(() => {
    if (timer) clearInterval(timer)
    if (modelTimer) clearTimeout(modelTimer)
    releaseTracks()
  })

  function toggleRecording(e: MouseEvent) {
    // DSFR shows a tooltip on focus as well as hover, and a click leaves the
    // button focused, so the notice would sit there until you clicked away.
    // `detail` is 0 when the button was activated from the keyboard, where
    // focus must stay put and the tooltip is the accessible behaviour.
    if (e.detail > 0) (e.currentTarget as HTMLElement).blur()

    if (recording) {
      stop()
      return
    }
    // Recording and the error state both paint the box red and both speak into
    // the same live region, so an old error clears before one starts and the
    // two are never on at once.
    error = undefined
    gate(start)
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
        { 'cl-recording': recording, 'cl-reserve-controls': !!voice }
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
      <!-- On the microphone's line rather than over the text. The box is three
           rows in a conversation, and a counter in the corner lands on a word. -->
      <p
        class={[
          'cl-recording-badge bottom-3 gap-2 text-sm absolute flex items-center',
          submitBtn ? 'right-23' : 'right-12'
        ]}
      >
        <span class="cl-recording-dot"></span>
        <span>{elapsed}</span>
      </p>
    {/if}
    {#if showModel}
      <!-- Slides out of the microphone, on the microphone's own line. The strip
           it sits in is reserved below the text, so it covers nothing. -->
      <p
        class={['cl-model-chip bottom-3 text-xs absolute', submitBtn ? 'right-23' : 'right-12']}
        aria-live="polite"
      >
        {m['voice.transcribedBy']({ model: shortModel })}
      </p>
    {/if}
    {#if voice}
      <Button
        icon={micIcon}
        iconOnly
        size="sm"
        variant="tertiary-no-outline"
        disabled={transcribing}
        aria-label={recording ? m['voice.stop']() : m['voice.start']()}
        aria-describedby={showHint ? `mic-hint-${id}` : undefined}
        onclick={toggleRecording}
        class={[
          'cl-mic bottom-3 absolute',
          submitBtn ? 'right-14' : 'right-3',
          { 'cl-mic-busy': transcribing }
        ]}
      />
      {#if showHint}
        <!-- The same markup Tooltip.svelte renders, so this reads like every
             other tooltip on the platform. DSFR's own script binds it to the
             button through aria-describedby. -->
        <span
          id="mic-hint-{id}"
          class="fr-tooltip fr-placement font-normal z-2000! normal-case"
          role="tooltip"
          {@attach teleport('tooltips')}
        >
          {voice.notice}
        </span>
      {/if}
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
      <!-- The red box and the ticking counter say this on screen. The sentence
           stays for the live region, which is all a screen reader has. -->
      <p class="fr-message sr-only">{m['voice.recording']()}</p>
    {:else if transcribing}
      <!-- Said by the spinning microphone on screen. As a visible line it pushed
           the page down for as long as the provider took, then let it back up. -->
      <p class="fr-message sr-only">{m['voice.transcribing']()}</p>
    {/if}
  </div>
</div>

<style lang="postcss">
  .fr-input {
    --border-plain-grey: var(--blue-france-main-525);
  }

  /* The microphone, the send button, the counter and the model chip all sit on
     the bottom line of the box. Reserving the strip is what keeps them off the
     text, and reserving it always means nothing reflows when one appears. */
  .cl-reserve-controls {
    padding-bottom: 2.75rem !important;
  }

  /* Marianne red, not the DSFR error red: the error state already owns that
     colour and this box can be recording without anything being wrong. */
  .cl-recording {
    --border-plain-grey: var(--red-marianne-425-625);
    background-color: var(--red-marianne-975-75) !important;
  }

  /* Quieter and smaller than the send button next to it: dictating is an
     alternative to typing, not the thing the box is for. */
  :global(.cl-mic) {
    color: var(--text-mention-grey);
    padding: 0.25rem !important;
    min-height: 2rem !important;
    min-width: 2rem;
    justify-content: center;
  }

  /* DSFR gives the icon a right margin for buttons that also carry text. This
     one carries none, so the margin pushes the glyph off centre. */
  :global(.cl-mic::before) {
    margin: 0 !important;
  }

  :global(.cl-mic:hover) {
    color: var(--text-title-blue-france);
  }

  /* DSFR paints a disabled button almost white. This one is not dead, it is
     working, so it keeps the microphone's own colour. */
  :global(.cl-mic-busy) {
    color: var(--text-mention-grey) !important;
  }

  :global(.cl-mic-busy::before) {
    animation: cl-mic-spin 1s linear infinite;
  }

  @keyframes cl-mic-spin {
    to {
      transform: rotate(360deg);
    }
  }

  /* Still says something is happening, without the spin. */
  @media (prefers-reduced-motion: reduce) {
    :global(.cl-mic-busy::before) {
      animation: cl-mic-pulse 1.2s ease-in-out infinite;
    }
  }

  @keyframes cl-mic-pulse {
    50% {
      opacity: 0.2;
    }
  }

  /* Same colour as the send button, so the chip reads as the box's own. */
  .cl-model-chip {
    margin: 0;
    display: flex;
    align-items: center;
    height: 2rem;
    padding: 0 0.625rem;
    border-radius: 1rem;
    white-space: nowrap;
    font-weight: 700;
    color: var(--text-inverted-blue-france);
    background-color: var(--blue-france-main-525);
    animation: cl-model-chip-out 0.25s ease-out;
  }

  /* Out of the microphone rather than into place from nowhere: the button is
     what produced the text, so the name comes from under it. */
  @keyframes cl-model-chip-out {
    from {
      opacity: 0;
      transform: translateX(1.5rem) scale(0.8);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .cl-model-chip {
      animation: none;
    }
  }

  /* Same height as the buttons it shares the line with, so it sits on their
     centre rather than on their bottom edge. */
  .cl-recording-badge {
    margin: 0;
    height: 2rem;
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
