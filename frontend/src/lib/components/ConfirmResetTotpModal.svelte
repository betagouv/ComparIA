<script lang="ts">
  import { Button, Modal } from '$components/dsfr'

  let {
    email,
    onConfirm
  }: {
    email: string | null
    onConfirm: () => void
  } = $props()

  function closeModal() {
    const el = document.getElementById('fr-modal-reset-totp')
    if (el) {
      // @ts-expect-error - DSFR is globally available
      window.dsfr(el).modal.conceal()
    }
  }

  function confirm() {
    onConfirm()
    closeModal()
  }
</script>

<Modal id="fr-modal-reset-totp" titleId="fr-modal-title-reset-totp">
  <h2 id="fr-modal-title-reset-totp" class="fr-modal__title">Reset two-factor authentication</h2>
  <p>
    Forget the authenticator app of {email}? They will be signed out everywhere and asked to set up
    a new one the next time they open the admin area.
  </p>
  <p class="fr-text--sm text-grey">
    Only do this for someone who asked you to, over a channel you trust: their email code alone then
    opens the admin area again.
  </p>
  <div class="fr-btns-group fr-btns-group--inline-md">
    <Button text="Cancel" variant="secondary" onclick={closeModal} />
    <Button text={email ? `Reset 2FA for ${email}` : 'Reset 2FA'} onclick={confirm} />
  </div>
</Modal>
