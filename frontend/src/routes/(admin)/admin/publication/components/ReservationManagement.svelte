<script lang="ts">
  import { Button, Modal } from '$components/dsfr'
  import { api, type ApiError } from '$lib/fastapi-client'
  import type { AdminPublishStatus } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { closeModal } from './modal'

  let { status, onreleased }: { status: AdminPublishStatus; onreleased: () => Promise<void> } =
    $props()

  let busy = $state(false)

  async function release() {
    const count = status.reserved
    busy = true
    try {
      await api.request('/admin/publishing/reservations', { method: 'DELETE' })
      useToast(m['admin.publishing.releaseSuccess']({ count }), 4000)
      closeModal('fr-modal-release-reserved')
      await onreleased()
    } catch (error) {
      useToast((error as ApiError).message, 6000, 'error')
    } finally {
      busy = false
    }
  }
</script>

<!-- Not the main use: reserving is meant to last. Kept apart, at the end. -->
<section class="mt-10 pt-6 border-t border-[--border-default-grey]">
  <h2 class="fr-h6 mb-2!">{m['admin.publishing.manageTitle']()}</h2>
  <p class="fr-text--sm text-grey mb-4!">{m['admin.publishing.reservedHelp']()}</p>
  <Button
    size="sm"
    variant="secondary"
    text={m['admin.publishing.releaseAll']()}
    disabled={busy || !status.reserved}
    aria-controls="fr-modal-release-reserved"
    data-fr-opened="false"
  />
</section>

<Modal
  id="fr-modal-release-reserved"
  titleId="fr-modal-title-release-reserved"
  headerClass="md:absolute! md:top-4 md:right-8 md:z-10 md:p-0!"
  contentClass="md:pt-4! mb-6!"
>
  <h2 id="fr-modal-title-release-reserved" class="fr-modal__title">
    {m['admin.publishing.releaseTitle']({ count: status.reserved })}
  </h2>
  <p>{m['admin.publishing.releaseWarning']({ sent: status.reserved_sent })}</p>

  <div class="mt-6 gap-4 sm:flex-row sm:justify-end flex flex-col-reverse">
    <Button
      variant="secondary"
      text={m['admin.publishing.cancel']()}
      disabled={busy}
      onclick={() => closeModal('fr-modal-release-reserved')}
    />
    <Button text={m['admin.publishing.releaseConfirm']()} disabled={busy} onclick={release} />
  </div>
</Modal>
