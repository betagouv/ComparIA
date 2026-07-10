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
    const el = document.getElementById('fr-modal-promote-admin')
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

<Modal id="fr-modal-promote-admin" titleId="fr-modal-title-promote-admin">
  <h2 id="fr-modal-title-promote-admin" class="fr-modal__title">Promote to admin</h2>
  <p>Promote {email} to admin? They will gain full admin access.</p>
  <div class="fr-btns-group fr-btns-group--inline-md">
    <Button text="Cancel" variant="secondary" onclick={closeModal} />
    <Button text="Promote" onclick={confirm} />
  </div>
</Modal>
