<script lang="ts">
  import { browser } from '$app/env'
  import { Modal } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { getCohortContext } from '$lib/stores/cohortStore.svelte'
  import { getSurveyContext } from '$lib/survey.svelte'
  import { SurveyForm } from './layout'

  const modalId = 'fr-modal-survey'
  const survey = getSurveyContext()
  const cohorts = getCohortContext()
  // Decided once, when the popup mounts: whether there is anything to ask and
  // whether this visitor has already been offered the popup.
  // FIXME hardcoded: do not show survey for 'pix' cohorts
  const show = browser && cohorts !== 'pix' && !!survey.hasNeverAnsweredQuestions

  // The DSFR modal script discloses on a change of data-fr-opened, not on its
  // initial value, so the attribute has to start false and flip once DSFR has
  // registered the button.
  let opened = $state(false)
</script>

{#if show}
  <!-- Opened programmatically, not by a visible trigger: this hidden button
       is what tells the DSFR modal script to disclose it once, on mount. -->
  <button class="hidden" data-fr-opened={opened} aria-controls={modalId}>Hidden</button>

  <Modal
    id={modalId}
    titleId="form-{modalId}-title"
    sizeClass="fr-col-12 fr-col-md-8 fr-col-lg-6"
    teleport
  >
    <SurveyForm
      id="form-{modalId}"
      title={m['survey.afterVote.title']()}
      description={m['survey.afterVote.description']()}
      onlyUnanswered
      dismissible
      {modalId}
      class="mt-5"
      onSuccess={() => (opened = false)}
    />
  </Modal>
{/if}
