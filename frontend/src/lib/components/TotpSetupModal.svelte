<script lang="ts">
  import Copy from '$components/Copy.svelte'
  import { Alert, Button, Modal } from '$components/dsfr'
  import TotpCodeInput from '$components/TotpCodeInput.svelte'
  import { api, type ApiError } from '$lib/fastapi-client'
  import { m } from '$lib/i18n/messages'
  import { onMount, tick } from 'svelte'

  const MODAL_ID = 'totp-setup-modal'

  let {
    enabled,
    onEnrolled
  }: {
    // An authenticator already in force: a code from it is asked first.
    enabled: boolean
    onEnrolled: () => void
  } = $props()

  interface Setup {
    secret: string
    otpauth_uri: string
    qr_svg: string
  }

  // 'current': prove the old device; 'loading': fetching a secret;
  // 'scan': QR shown, waiting for a code from the new device.
  let phase = $state<'current' | 'loading' | 'scan'>('loading')
  let setup = $state<Setup>()
  let currentCode = $state('')
  let code = $state('')
  let busy = $state(false)
  let error = $state<string>()
  let container = $state<HTMLElement>()

  // Four-character groups read aloud and type in far better than 32 in a row.
  const groupedSecret = $derived(setup?.secret.match(/.{1,4}/g)?.join(' ') ?? '')

  function dsfrModal() {
    const el = document.getElementById(MODAL_ID)
    // @ts-expect-error - DSFR is globally available
    return el ? window.dsfr(el).modal : undefined
  }

  function reset() {
    // Back to 'loading', or a reopened modal would show the failure branch
    // while the next secret is being fetched.
    phase = 'loading'
    setup = undefined
    currentCode = ''
    code = ''
    error = undefined
    busy = false
  }

  // The secret must not linger in the DOM once the modal is closed. DSFR
  // announces closing with this event; Modal's own onClose fires on blur,
  // which also happens when focus moves into the form.
  onMount(() => {
    const el = document.getElementById(MODAL_ID)
    el?.addEventListener('dsfr.conceal', reset)
    return () => el?.removeEventListener('dsfr.conceal', reset)
  })

  export async function start() {
    reset()
    dsfrModal()?.disclose()
    if (enabled) {
      phase = 'current'
      await focus('#totp-current-code')
    } else {
      await requestSecret()
    }
  }

  async function focus(selector: string) {
    await tick()
    container?.querySelector<HTMLInputElement>(selector)?.focus()
  }

  function describe(err: unknown): string {
    const { status, message } = err as ApiError
    if (status === 429) return m['auth.settings.totp.modal.tooMany']()
    if (status === 409) return m['auth.settings.totp.modal.expired']()
    if (status === 401 || status === 403) return m['auth.settings.totp.modal.sessionExpired']()
    // An authenticator got enrolled elsewhere since this page loaded: the
    // backend now wants a code from it before handing out a new secret.
    if (status === 400 && message.includes('totp_code_required'))
      return m['auth.settings.totp.modal.restart']()
    return m['auth.settings.totp.modal.invalid']()
  }

  async function requestSecret() {
    busy = true
    error = undefined
    try {
      const body = enabled ? { code: currentCode } : {}
      setup = await api.request<Setup>('/auth/totp/setup', {
        method: 'POST',
        body: JSON.stringify(body)
      })
      phase = 'scan'
      busy = false
      await focus('#totp-confirm-code')
    } catch (err) {
      error = describe(err)
      // No device to prove yet on a first enrolment: nothing to retry with.
      if (!enabled) phase = 'scan'
    } finally {
      busy = false
    }
  }

  async function confirm() {
    busy = true
    error = undefined
    try {
      await api.request('/auth/totp/confirm', {
        method: 'POST',
        body: JSON.stringify({ code })
      })
      dsfrModal()?.conceal()
      reset()
      onEnrolled()
    } catch (err) {
      error = describe(err)
    } finally {
      busy = false
    }
  }

  function onSubmit(e: SubmitEvent) {
    e.preventDefault()
    if (phase === 'current') requestSecret()
    else if (phase === 'scan' && setup) confirm()
  }
</script>

<Modal id={MODAL_ID} titleId="totp-setup-title" sizeClass="fr-col-12 fr-col-md-8 fr-col-lg-6">
  <div bind:this={container}>
    <h2 id="totp-setup-title" class="fr-modal__title">{m['auth.settings.totp.modal.title']()}</h2>

    <form onsubmit={onSubmit}>
      {#if phase === 'current'}
        <p>{m['auth.settings.totp.modal.currentHelp']()}</p>
        <TotpCodeInput
          id="totp-current-code"
          bind:value={currentCode}
          label={m['auth.settings.totp.modal.currentLabel']()}
          {error}
          disabled={busy}
        />
        <div class="fr-btns-group fr-btns-group--inline-reverse fr-btns-group--inline-lg">
          <Button
            type="submit"
            text={m['auth.settings.totp.modal.continue']()}
            disabled={busy || currentCode.length !== 6}
          />
          <Button variant="secondary" text={m['words.cancel']()} aria-controls={MODAL_ID} />
        </div>
      {:else if phase === 'loading'}
        <p aria-live="polite">{m['auth.settings.totp.modal.loading']()}</p>
      {:else}
        {#if setup}
          <p>{m['auth.settings.totp.modal.scanHelp']()}</p>
          <div class="gap-2 my-4 flex flex-col items-center">
            <img
              src={setup.qr_svg}
              alt={m['auth.settings.totp.modal.qrAlt']()}
              width="200"
              height="200"
              class="rounded bg-white p-2"
            />
          </div>
          <p class="mb-1!">{m['auth.settings.totp.modal.manualKey']()}</p>
          <div class="gap-2 mb-4 flex items-center">
            <!-- ARIA gives role "code" no accessible name, so the label is read as text. -->
            <span class="sr-only">{m['auth.settings.totp.modal.manualKeyLabel']()}</span>
            <code class="fr-text--md break-all">{groupedSecret}</code>
            <Copy
              value={setup.secret}
              labels={{ do: m['actions.copyKey.do'](), done: m['actions.copyKey.done']() }}
            />
          </div>
          <TotpCodeInput
            id="totp-confirm-code"
            bind:value={code}
            label={m['auth.settings.totp.modal.confirmLabel']()}
            {error}
            disabled={busy}
          />
          {#if enabled}
            <p class="fr-text--sm text-grey">{m['auth.settings.totp.modal.otherSessions']()}</p>
          {/if}
        {:else}
          <!-- The secret could not be fetched: the message lands here. -->
          <Alert variant="error" title={m['auth.settings.totp.modal.failedTitle']()} class="mb-4">
            <p>{error}</p>
          </Alert>
        {/if}
        <div class="fr-btns-group fr-btns-group--inline-reverse fr-btns-group--inline-lg">
          {#if setup}
            <Button
              type="submit"
              text={busy
                ? m['auth.settings.totp.modal.confirming']()
                : m['auth.settings.totp.modal.confirm']()}
              disabled={busy || code.length !== 6}
            />
          {:else}
            <Button
              type="button"
              text={m['words.retry']()}
              disabled={busy}
              onclick={requestSecret}
            />
          {/if}
          <Button variant="secondary" text={m['words.cancel']()} aria-controls={MODAL_ID} />
        </div>
      {/if}
    </form>
  </div>
</Modal>
