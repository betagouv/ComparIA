<script lang="ts">
  import { Icon } from '$components/dsfr'
  import type { APIModeAndPromptData } from '$lib/chatService.svelte'
  import { modeInfos as modeChoices } from '$lib/chatService.svelte'
  import Dropdown from '$lib/components/Dropdown.svelte'
  import ModelsSelection from '$lib/components/ModelsSelection.svelte'
  import { m } from '$lib/i18n/messages'
  import type { BotModel } from '$lib/models'
  import { fade } from 'svelte/transition'

  let {
    models,
    mode = $bindable(),
    modelsSelection = $bindable(),
    disabled = false
  }: {
    models: BotModel[]
    mode: APIModeAndPromptData['mode']
    modelsSelection: string[]
    disabled?: boolean
  } = $props()

  let neverClicked = $state(true)
  let showModelsSelection = $state(false)

  const choice = $derived(modeChoices.find((c) => c.value === mode) || modeChoices[0])
  const { modelA, modelB } = $derived({
    modelA: models.find((model) => model.id === modelsSelection[0]),
    modelB: models.find((model) => model.id === modelsSelection[1])
  })
  const altLabel = $derived.by(() => {
    if ((mode == 'custom' && modelsSelection.length < 1) || (mode == 'random' && neverClicked)) {
      return m['arenaHome.modelSelection']()
    } else {
      return choice.alt_label
    }
  })

  function toggleModelSelection(id: string): void {
    if (!modelsSelection.includes(id)) {
      if (modelsSelection.length < 2) {
        modelsSelection.push(id)
      }
    } else {
      modelsSelection = modelsSelection.filter((item) => item !== id)
    }

    // If clicked on second model, close model selection modal
    if (modelsSelection.length === 2) {
      const modeSelectionModal = document.getElementById('modal-mode-selection')
      if (modeSelectionModal) {
        window.setTimeout(() => {
          // @ts-ignore - DSFR is globally available
          window.dsfr(modeSelectionModal).modal.conceal()
        }, 300)
      }
    }
  }
</script>

<div class="selections">
  <button
    class="mode-selection-btn fr-py-1w fr-py-md-0 fr-mb-md-0 fr-mb-1w fr-mr-3v"
    data-fr-opened="false"
    {disabled}
    aria-controls="modal-mode-selection"
    onclick={() => {
      neverClicked = false
      showModelsSelection = false
    }}
  >
    <Icon icon="equalizer-fill" size="sm" block class="text-primary" />
    <span class="label">{altLabel}</span>
    <Icon icon="arrow-down-s-line" size="sm" />
  </button>
  {#if mode == 'custom' && modelA}
    <button
      {disabled}
      class="model-selection fr-mb-md-0 fr-mb-1w"
      data-fr-opened="false"
      aria-controls="modal-mode-selection"
    >
      <img
        src="/orgs/ai/{modelA.icon_path}"
        alt={modelA.simple_name}
        width="20"
        class="fr-mr-1v inline"
      />&thinsp;{modelA.simple_name}
      <strong class="versus">&nbsp;vs.&nbsp;</strong>
      {#if modelB}
        <img
          src="/orgs/ai/{modelB.icon_path}"
          alt={modelB.simple_name}
          width="20"
          class="fr-mr-1v inline"
        />&thinsp;{modelB.simple_name}
      {:else}
        {m['words.random']()}
      {/if}
    </button>
  {/if}
</div>

<dialog aria-labelledby="modal-mode-selection" id="modal-mode-selection" class="fr-modal">
  <div class="fr-container fr-container--fluid fr-container-md">
    <div class="fr-grid-row fr-grid-row--center">
      <div
        class="fr-col-12"
        class:fr-col-md-10={showModelsSelection}
        class:fr-col-md-5={!showModelsSelection}
      >
        <div class="fr-modal__body">
          <div class="fr-modal__header">
            <button
              class="fr-btn--close fr-btn"
              title="Fermer la fenêtre modale"
              aria-controls="modal-mode-selection"
            >
              {m['words.close']()}
            </button>
          </div>
          <div class="fr-modal__content fr-pb-4w">
            {#if showModelsSelection == false}
              <h6 id="modal-mode-selection" class="modal-title">
                {m['arenaHome.selectModels.question']()}
              </h6>
              <p>{m['arenaHome.selectModels.help']()}</p>
              <div>
                <Dropdown
                  bind:mode
                  choices={modeChoices}
                  onOptionSelected={(mode) => (showModelsSelection = mode === 'custom')}
                />
              </div>
            {:else}
              <div in:fade>
                <h6 id="modal-mode-selection" class="modal-title">
                  {m['arenaHome.compareModels.question']()}
                  <span class="text-purple fr-ml-2w">
                    {m['arenaHome.compareModels.count']({ count: modelsSelection.length })}
                  </span>
                </h6>
                <p class="fr-mb-2w">
                  {m['arenaHome.compareModels.help']()}
                </p>
                <div>
                  <ModelsSelection
                    {models}
                    bind:selection={modelsSelection}
                    {toggleModelSelection}
                  />
                  <div class="fr-mt-2w">
                    <button
                      class="btn fr-mb-md-0 fr-mb-1w"
                      onclick={() => (showModelsSelection = false)}
                    >
                      {m['words.back']()}
                    </button>
                    <button aria-controls="modal-mode-selection" class="btn purple-btn float-right">
                      {m['words.validate']()}
                    </button>
                  </div>
                </div>
              </div>
            {/if}
          </div>
        </div>
      </div>
    </div>
  </div>
</dialog>
