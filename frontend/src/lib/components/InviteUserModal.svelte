<script lang="ts">
  import { Button, Input, Modal } from '$components/dsfr'
  import { api } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'

  let { onSuccess }: { onSuccess?: () => void } = $props()

  let email = $state('')
  let loading = $state(false)
  let error = $state<string>()

  function closeModal() {
    const el = document.getElementById('fr-modal-invite-user')
    if (el) {
      // @ts-expect-error - DSFR is globally available
      window.dsfr(el).modal.conceal()
    }
  }

  async function invite(e: SubmitEvent) {
    e.preventDefault()
    loading = true
    error = undefined
    try {
      await api.request('/admin/users/invite', {
        method: 'POST',
        body: JSON.stringify({ email })
      })
      useToast(`Invitation sent to ${email}`, 4000)
      email = ''
      closeModal()
      onSuccess?.()
    } catch (err) {
      error = (err as Error).message
    } finally {
      loading = false
    }
  }
</script>

<Modal id="fr-modal-invite-user" titleId="fr-modal-title-invite-user">
  <h2 id="fr-modal-title-invite-user" class="fr-modal__title">Invite user</h2>
  <form onsubmit={invite}>
    <Input id="invite-user-email" type="email" label="Email" bind:value={email} {error} required />
    <Button type="submit" text="Send invite" disabled={loading || !email} class="mt-4!" />
  </form>
</Modal>
