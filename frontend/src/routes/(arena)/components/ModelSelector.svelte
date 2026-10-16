<script lang="ts">
  import { Badge, Button, Icon, Search } from '$components/dsfr'
  import { AILogo } from '$components/layout'
  import Selector from '$components/Selector.svelte'
  import type { APIModeAndPromptData, Mode } from '$lib/chatService.svelte'
  import { getModeInfos } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import type { PausedLLM } from '$lib/generated/backend'
  import type { BotModel } from '$lib/models'
  import { fade } from 'svelte/transition'
  import type { ModePause } from './pausedModes'
  import type { ClassValue } from 'svelte/elements'
  import { resetTime, spoken, type ResetTime } from './resetTime'
  import TimedText from './TimedText.svelte'

  let {
    models,
    mode = $bindable(),
    modelsSelection = $bindable(),
    disabled = false,
    paused = new Map(),
    pausedModes = new Map()
  }: {
    models: BotModel[]
    mode: APIModeAndPromptData['mode']
    modelsSelection: string[]
    disabled?: boolean
    /** The models a new comparison may not use yet, by id. */
    paused?: ReadonlyMap<string, PausedLLM>
    /** The modes left with nothing to draw, and when they come back. */
    pausedModes?: ReadonlyMap<Mode, ModePause>
  } = $props()

  // The note a greyed-out card carries: when it comes back.
  type Pause = { text: string; reset?: ResetTime; said: string }

  function note(text: string, reset?: ResetTime): Pause {
    return { text, reset, said: reset ? spoken(text, reset) : text }
  }

  function pausedUntil(until: string | null): Pause {
    const reset = resetTime(until)
    return note(m['arene.limits.picker.paused']({ until: reset.until }), reset)
  }

  function modelPause(id: string): Pause | undefined {
    const llm = paused.get(id)
    if (!llm) return undefined
    if (llm.reason === 'full') return note(m['arene.limits.picker.full']())
    return pausedUntil(llm.until)
  }

  function modePause(value: Mode): Pause | undefined {
    const pause = pausedModes.get(value)
    if (!pause) return undefined
    if (pause.full) return note(m['arene.limits.picker.full']())
    return pausedUntil(pause.until)
  }

  let neverClicked = $state(true)
  let showModelsSelection = $state(false)
  let search = $state('')

  const filteredModels = $derived.by(() => {
    const _search = search.toLowerCase()
    return models
      .filter((llm) => !_search || llm.search.includes(_search))
      .map((llm) => {
        const pause = modelPause(llm.id!)
        return { ...llm, label: llm.name, value: llm.id!, pause, disabledReason: pause?.said }
      })
  })

  const modeChoices = $derived(
    getModeInfos().map((info) => {
      const pause = modePause(info.value)
      return { ...info, pause, disabledReason: pause?.said }
    })
  )
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
      class="bg-white! px-3! text-sm! text-dark-grey! md:w-auto! xl:max-w-[260px] w-full! justify-start"
      style="--border-action-high-blue-france: var(--grey-925-125)"
      onclick={() => (showModelsSelection = true)}
    >
      <AILogo
        logo={modelA.lab.logo}
        customLogoId={modelA.lab.has_custom_logo ? modelA.lab.id : undefined}
        customLogoVersion={modelA.lab.logo_version}
        alt=""
        class="me-1 inline"
      />
      {modelA.name}
      <strong class="mx-2">VS</strong>
      {#if modelB}
        <AILogo
          logo={modelB.lab.logo}
          customLogoId={modelB.lab.has_custom_logo ? modelB.lab.id : undefined}
          customLogoVersion={modelB.lab.logo_version}
          alt=""
          class="me-1 inline"
        />
        {modelB.name}
      {:else}
        {m['words.random']()}
      {/if}
    </Button>
  {/if}
</div>

<!-- In a greyed-out card, outside its label so the card's name stays the
     model's; the input is described by it. -->
{#snippet pauseLine(id: string, pause: Pause, className: ClassValue)}
  <p {id} class={['cl-pause-line fr-text--xs mb-0!', className]}>
    <TimedText text={pause.text} reset={pause.reset} />
  </p>
{/snippet}

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
                <h2 id="modal-mode-selection-title" class="fr-h6 mb-3!">
                  {m['arenaHome.selectModels.question']()}
                </h2>
                <p class="mb-6!">{m['arenaHome.selectModels.help']()}</p>
              {:else}
                <div class="gap-3 md:flex-row flex w-full flex-col">
                  <div>
                    <h2 id="modal-mode-selection-title" class="fr-h6 mb-3!">
                      {m['arenaHome.compareModels.question']()}
                    </h2>
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
                kind="radio"
                label={m['arenaHome.selectModels.question']()}
                bind:value={mode}
                choices={modeChoices}
                containerClass="flex flex-col gap-3 md:gap-4"
                choiceClass="flex flex-col text-sm text-dark-grey!"
                onChange={(mode) => (showModelsSelection = mode === 'custom')}
              >
                {#snippet option(opt, labelProps, input)}
                  <div class={[labelProps.class, { 'cl-unavailable': !!opt.pause }]}>
                    <label for={labelProps.for} class="p-4 flex grow items-center">
                      {@render input(opt, {
                        // A paused mode is not picked, so the dialog stays open.
                        'aria-controls':
                          opt.value != 'custom' && !opt.pause ? 'modal-mode-selection' : ''
                      })}
                      <Icon icon={opt.icon} block class="text-primary me-3" />
                      {#if opt.value != 'custom'}
                        <span>
                          <strong>{opt.label}</strong>&nbsp;: {opt.description}
                        </span>
                      {:else}
                        <strong>{opt.label}</strong>
                        <Icon icon="i-ri-arrow-right-s-line" block size="sm" class="ms-auto" />
                      {/if}
                    </label>
                    {#if opt.pause}
                      {@render pauseLine(labelProps.reasonId, opt.pause, '-mt-3 ps-13 pe-4 pb-3')}
                    {/if}
                  </div>
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
                  label={m['arenaHome.compareModels.question']()}
                  bind:value={modelsSelection}
                  choices={filteredModels}
                  multiple
                  max={2}
                  containerClass="grid grid-cols-2 gap-3 md:grid-cols-3"
                  choiceClass="flex flex-col text-sm"
                  onChange={toggleModelSelection}
                >
                  {#snippet option(opt, labelProps, input)}
                    {@const modelBadges = (['license', 'release', 'size'] as const)
                      .map((k) => opt.badges[k])
                      .filter((b) => !!b)}

                    <div class={[labelProps.class, { 'cl-unavailable': !!opt.pause }]}>
                      <label for={labelProps.for} class="p-2 md:px-4 md:py-3 grow">
                        {@render input(opt)}
                        <div class="text-dark-grey flex">
                          <AILogo
                            logo={opt.lab.logo}
                            customLogoId={opt.lab.has_custom_logo ? opt.lab.id : undefined}
                            customLogoVersion={opt.lab.logo_version}
                            alt=""
                            class={['me-2', { 'cl-dimmed': !!opt.pause }]}
                          />
                          <span class="organisation md:inline hidden">{opt.lab.name}/</span><strong
                            >{opt.name}</strong
                          >
                        </div>
                        <ul class="fr-badges-group mt-3! md:flex! hidden!">
                          {#each modelBadges as badge, i (i)}
                            <li>
                              <Badge
                                {...badge}
                                id="{opt.value}-card-badge-{i}"
                                size="xs"
                                noTooltip
                              />
                            </li>
                          {/each}
                        </ul>
                      </label>
                      {#if opt.pause}
                        {@render pauseLine(
                          labelProps.reasonId,
                          opt.pause,
                          '-mt-1 px-2 pb-2 md:px-4 md:pb-3'
                        )}
                      {/if}
                    </div>
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

<style>
  .cl-pause-line {
    color: var(--text-mention-grey);
  }

  /* Greyed out as DSFR does a disabled card; the text it carries stays at
     4.5:1 or more on the grey background. */
  .cl-unavailable {
    color: var(--text-mention-grey) !important;

    & :global(.text-dark-grey),
    & :global(.text-primary) {
      color: inherit !important;
    }

    & :global(.cl-dimmed) {
      opacity: 0.5;
      filter: grayscale(1);
    }

    & :global(.fr-badge) {
      filter: grayscale(1);
    }
  }
</style>
