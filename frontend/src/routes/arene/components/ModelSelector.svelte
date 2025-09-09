<script lang="ts">
  import { Button, Icon } from '$components/dsfr'
  import type { APIModeAndPromptData } from '$lib/chatService.svelte'
  import { modeInfos as modeChoices } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import type { BotModel } from '$lib/models'
  import { fade } from 'svelte/transition'
  import { Dropdown, ModelsSelection } from '.'

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

<div class="flex flex-col gap-3 md:col-span-2 md:flex-row">
  <Button
    variant="secondary"
    native
    aria-controls="modal-mode-selection"
    {disabled}
    data-fr-opened="false"
    class="px-3! bg-white! text-dark-grey! text-sm! w-full! md:w-auto! items-center justify-start"
    style="--border-action-high-blue-france: var(--grey-925-125)"
    onclick={() => {
      neverClicked = false
      showModelsSelection = false
    }}
  >
    <Icon icon="equalizer-fill" size="sm" class="text-primary me-2" />
    <span class="label">{altLabel}</span>
    <Icon icon="arrow-down-s-line" size="sm" class="ms-auto md:ms-2" />
  </Button>

  {#if mode == 'custom' && modelA}
    <Button
      variant="secondary"
      native
      aria-controls="modal-mode-selection"
      {disabled}
      data-fr-opened="false"
      class="px-3! bg-white! text-dark-grey! text-sm! w-full! md:w-auto! justify-start"
      style="--border-action-high-blue-france: var(--grey-925-125)"
      onclick={() => (showModelsSelection = true)}
    >
      <img
        src="/orgs/ai/{modelA.icon_path}"
        alt={modelA.simple_name}
        width="20"
        class="fr-mr-1v inline"
      />
      {modelA.simple_name}
      <strong class="mx-2">VS</strong>
      {#if modelB}
        <img
          src="/orgs/ai/{modelB.icon_path}"
          alt={modelB.simple_name}
          width="20"
          class="fr-mr-1v inline"
        />
        {modelB.simple_name}
      {:else}
        {m['words.random']()}
      {/if}
    </Button>
  {/if}
</div>

<dialog aria-labelledby="modal-mode-selection-title" id="modal-mode-selection" class="fr-modal">
  <div class="fr-container fr-container--fluid fr-container-md">
    <div class="fr-grid-row fr-grid-row--center">
      <div
        class="fr-col-12"
        class:fr-col-md-10={showModelsSelection}
        class:fr-col-md-5={!showModelsSelection}
      >
        <div class="fr-modal__body rounded-xl">
          <div class="fr-modal__header">
            <Button
              variant="tertiary-no-outline"
              text={m['words.close']()}
              title={m['closeModal']()}
              aria-controls="modal-mode-selection"
              class="fr-btn--close"
            />
          </div>
          <div class="fr-modal__content pb-8!">
            {#if showModelsSelection == false}
              <h6 id="modal-mode-selection-title" class="mb-3!">
                {m['arenaHome.selectModels.question']()}
              </h6>
              <p class="mb-6!">{m['arenaHome.selectModels.help']()}</p>

              <Dropdown
                bind:mode
                choices={modeChoices}
                onOptionSelected={(mode) => (showModelsSelection = mode === 'custom')}
              />
            {:else}
              <div in:fade>
                <h6 id="modal-mode-selection" class="mb-3! flex flex-wrap gap-4 md:gap-6">
                  {m['arenaHome.compareModels.question']()}
                  <span class="text-primary">
                    {m['arenaHome.compareModels.count']({ count: modelsSelection.length })}
                  </span>
                </h6>
                <p class="mb-5! md:mb-8!">
                  {m['arenaHome.compareModels.help']()}
                </p>

                <div>
                  <ModelsSelection
                    {models}
                    bind:selection={modelsSelection}
                    {toggleModelSelection}
                  />
                </div>
              </div>
            {/if}
          </div>
          {#if showModelsSelection == true}
            <div class="fr-modal__footer p-4! md:px-5!">
              <div
                class="fr-btns-group fr-btns-group--right fr-btns-group--inline-lg fr-btns-group--icon-left"
              >
                <Button
                  text={m['words.back']()}
                  variant="tertiary"
                  class="md:me-auto!"
                  onclick={() => (showModelsSelection = false)}
                />

                <Button
                  aria-controls="modal-mode-selection"
                  text={m['words.validate']()}
                  class=""
                />
              </div>
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>
</dialog>
