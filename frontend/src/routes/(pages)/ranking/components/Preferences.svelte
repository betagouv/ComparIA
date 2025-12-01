<script lang="ts">
  import { Link, Modal } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { PreferencesTable } from '.'

  let { onDownloadData }: { onDownloadData: () => void } = $props()
</script>

<div id="ranking-preferences">
  <h2 class="fr-h6 text-primary! mb-4!">{m['ranking.preferences.title']()}</h2>
  <p class="text-dark-grey mb-4! text-[14px]!">{m['ranking.preferences.desc']()}</p>
  <p class="mb-4!">
    <Link
      href="#"
      native={false}
      text={m['ranking.preferences.modal.cta']()}
      data-fr-opened="false"
      aria-controls="preferences-modal"
      class="text-[14px]!"
    />
  </p>

  <Modal
    id="preferences-modal"
    titleId="preferences-modal-title"
    sizeClass="fr-col-12 fr-col-md-10"
  >
    <h6 id="preferences-modal-title" class="text-dark-grey! mb-3!">
      {m['ranking.preferences.modal.title']()}
    </h6>

    <!-- FIXME alt -->
    <img src="/ranking/preferences.png" />
  </Modal>

  <PreferencesTable id="preferences-table" {onDownloadData} />
</div>
