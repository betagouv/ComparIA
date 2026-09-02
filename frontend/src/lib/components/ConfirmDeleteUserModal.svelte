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
    const el = document.getElementById('fr-modal-delete-user')
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

<Modal id="fr-modal-delete-user" titleId="fr-modal-title-delete-user">
  <h2 id="fr-modal-title-delete-user" class="fr-modal__title">Delete user</h2>
  <p>Delete {email}? This cannot be undone.</p>
  <div class="fr-btns-group fr-btns-group--inline-md">
    <Button text="Cancel" variant="secondary" onclick={closeModal} />
    <!-- Name states target and permanence so the action is unambiguous out of context (RGAA 11.9). -->
    <Button
      text={email ? `Delete ${email} permanently` : 'Delete user permanently'}
      onclick={confirm}
    />
  </div>
</Modal>
