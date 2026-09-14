<script lang="ts">
  import { Button, Modal } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'

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
  <h2 id="fr-modal-title-reset-totp" class="fr-modal__title">
    {m['admin.users.resetTotp.title']()}
  </h2>
  <p>{m['admin.users.resetTotp.intro']({ email: email ?? '' })}</p>
  <p class="fr-text--sm text-grey">{m['admin.users.resetTotp.warning']()}</p>
  <div class="fr-btns-group fr-btns-group--inline-md">
    <Button text={m['words.cancel']()} variant="secondary" onclick={closeModal} />
    <Button text={m['admin.users.resetTotp.confirm']({ email: email ?? '' })} onclick={confirm} />
  </div>
</Modal>
