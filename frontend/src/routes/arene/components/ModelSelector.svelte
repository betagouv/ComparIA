<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import { Badge, Button, Icon, Search } from '$components/dsfr'
  import Selector from '$components/Selector.svelte'
  import type { APIModeAndPromptData } from '$lib/chatService.svelte'
  import { modeInfos as modeChoices } from '$lib/chatService.svelte'
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
  let search = $state('')

  const filteredModels = $derived.by(() => {
    const _search = search.toLowerCase()
    return models
      .filter((m) => !_search || m.search.includes(_search))
      .map((m) => ({
        ...m,
        label: m.simple_name,
        value: m.id
      }))
  })

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

  function toggleModelSelection(): void {
    // If clicked on second model, close model selection modal
    if (modelsSelection.length === 2) {
      const modeSelectionModal = document.getElementById('modal-mode-selection')
      if (modeSelectionModal) {
        window.setTimeout(() => {
          // @ts-expect-error - DSFR is globally available
          window.dsfr(modeSelectionModal).modal.conceal()
        }, 300)
      }
    }
  }
</script>

<div class="gap-3 md:col-span-5 md:flex-row flex flex-col">
  <Button
    variant="secondary"
    native
    aria-controls="modal-mode-selection"
    {disabled}
    data-fr-opened="false"
    class="bg-white! px-3! text-sm! text-dark-grey! md:w-auto! w-full! items-center justify-start"
    style="--border-action-high-blue-france: var(--grey-925-125)"
    onclick={() => {
      neverClicked = false
      showModelsSelection = false
    }}
  >
    <Icon icon="i-ri-equalizer-fill" block size="sm" class="text-primary me-2" />
    <span class="label">{altLabel}</span>
    <Icon icon="i-ri-arrow-down-s-line" block size="sm" class="md:ms-2 ms-auto" />
  </Button>

  {#if mode == 'custom' && modelA}
    <Button
      variant="secondary"
      native
      aria-controls="modal-mode-selection"
      {disabled}
      data-fr-opened="false"
      class="bg-white! px-3! text-sm! text-dark-grey! md:w-auto! w-full! justify-start"
      style="--border-action-high-blue-france: var(--grey-925-125)"
      onclick={() => (showModelsSelection = true)}
    >
      <AILogo iconPath={modelA.icon_path} alt={modelA.simple_name} class="me-1 inline" />
      {modelA.simple_name}
      <strong class="mx-2">VS</strong>
      {#if modelB}
        <AILogo iconPath={modelB.icon_path} alt={modelB.simple_name} class="me-1 inline" />
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
          <div
            class={[
              'fr-modal__header bg-white flex-col!',
              { 'top-0 md:sticky z-1': showModelsSelection }
            ]}
          >
            <Button
              variant="tertiary-no-outline"
              text={m['words.close']()}
              title={m['closeModal']()}
              aria-controls="modal-mode-selection"
              class="fr-btn--close"
            />

            <div class="mt-2 w-full self-start">
              {#if showModelsSelection == false}
                <h6 id="modal-mode-selection-title" class="mb-3!">
                  {m['arenaHome.selectModels.question']()}
                </h6>
                <p class="mb-6!">{m['arenaHome.selectModels.help']()}</p>
              {:else}
                <div class="gap-3 md:flex-row flex w-full flex-col">
                  <div>
                    <h6 id="modal-mode-selection" class="mb-3!">
                      {m['arenaHome.compareModels.question']()}
                    </h6>
                    <p class="mb-0!">
                      {m['arenaHome.compareModels.help']()}
                    </p>
                  </div>

                  <Search
                    id="model-list-search"
                    bind:value={search}
                    label={m['actions.searchModel']()}
                    class="md:ms-auto md:w-auto w-full self-end"
                  />
                </div>
              {/if}
            </div>
          </div>
          <div class="fr-modal__content m-0! pb-12!">
            {#if showModelsSelection == false}
              <Selector
                id="mode-selector"
                bind:value={mode}
                choices={modeChoices}
                containerClass="flex flex-col gap-3 md:gap-4"
                choiceClass="flex items-center p-4 text-sm text-dark-grey!"
                onChange={(mode) => (showModelsSelection = mode === 'custom')}
              >
                {#snippet option(opt, labelProps, input)}
                  <label {...labelProps}>
                    {@render input(opt, {
                      'aria-controls': opt.value != 'custom' ? 'modal-mode-selection' : ''
                    })}
                    <Icon icon={opt.icon} block class="text-primary me-3" />
                    {#if opt.value != 'custom'}
                      <div>
                        <strong>{opt.label}</strong>&nbsp;: {opt.description}
                      </div>
                    {:else}
                      <strong>{opt.label}</strong>
                      <Icon icon="i-ri-arrow-right-s-line" block size="sm" class="ms-auto" />
                    {/if}
                  </label>
                {/snippet}
              </Selector>
            {:else}
              <div in:fade class="my-4">
                {#if filteredModels.length === 0}
                  <p>{m['models.list.noresults']()}</p>
                {/if}

                <Selector
                  id="models-selector"
                  kind="checkbox"
                  bind:value={modelsSelection}
                  choices={filteredModels}
                  multiple
                  max={2}
                  containerClass="grid grid-cols-2 gap-3 md:grid-cols-3"
                  choiceClass="text-sm p-2 md:px-4 md:py-3"
                  onChange={toggleModelSelection}
                >
                  {#snippet option(opt, labelProps, input)}
                    {@const modelBadges = (['license', 'releaseDate', 'size'] as const)
                      .map((k) => opt.badges[k])
                      .filter((b) => !!b)}

                    <label {...labelProps}>
                      {@render input(opt)}
                      <div class="text-dark-grey flex">
                        <AILogo iconPath={opt.icon_path} alt={opt.organisation} class="me-2" />
                        <span class="organisation md:inline hidden">{opt.organisation}/</span
                        ><strong>{opt.simple_name}</strong>
                      </div>
                      <ul class="fr-badges-group mt-3! md:flex! hidden!">
                        {#each modelBadges as badge, i (i)}
                          <li><Badge id="card-badge-{i}" size="xs" {...badge} noTooltip /></li>
                        {/each}
                      </ul>
                    </label>
                  {/snippet}
                </Selector>
              </div>
            {/if}
          </div>
          {#if showModelsSelection == true}
            <div class="fr-modal__footer p-4! md:px-5!">
              <div class="gap-4 md:flex-row flex w-full flex-col-reverse">
                <Button
                  text={m['words.back']()}
                  variant="tertiary"
                  class="md:me-auto! md:w-auto! w-full!"
                  icon="arrow-left-line"
                  onclick={() => (showModelsSelection = false)}
                />

                <div class="gap-4 md:flex-row flex flex-col">
                  <p class="mb-0! text-primary font-bold md:self-center">
                    {m['arenaHome.compareModels.count']({ count: modelsSelection.length })}
                  </p>

                  <Button
                    aria-controls="modal-mode-selection"
                    text={m['words.validate']()}
                    disabled={!modelsSelection.length}
                    class="md:w-auto! w-full!"
                  />
                </div>
              </div>
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>
</dialog>
