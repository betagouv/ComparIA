<script lang="ts">
  import { Badge, Button, Icon, Search } from '$components/dsfr'
  import { AILogo } from '$components/layout'
  import Selector from '$components/Selector.svelte'
  import type { APIModeAndPromptData, Mode } from '$lib/chatService.svelte'
  import { getModeInfos } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import type { PausedLLM } from '$lib/generated/backend'
  import type { Spent } from '$lib/limits.svelte'
  import type { BotModel } from '$lib/models'
  import { fade } from 'svelte/transition'
  import LimitHint from './LimitHint.svelte'
  import type { ModePause } from './pausedModes'
  import { FULL_ICON, PAUSED_ICON, TIME_SLOT, resetTime, spoken, type ResetTime } from './resetTime'
  import TimedText from './TimedText.svelte'

  let {
    models,
    mode = $bindable(),
    modelsSelection = $bindable(),
    disabled = false,
    paused = new Map(),
    expensive,
    pausedModes = new Map()
  }: {
    models: BotModel[]
    mode: APIModeAndPromptData['mode']
    modelsSelection: string[]
    disabled?: boolean
    /** The models a new comparison may not use yet, by id. */
    paused?: ReadonlyMap<string, PausedLLM>
    /** Set while the expensive allowance is spent, for whom and until when. */
    expensive?: Spent
    /** The modes left with nothing to draw, and when they come back. */
    pausedModes?: ReadonlyMap<Mode, ModePause>
  } = $props()

  type Pause = { chip: string; icon: string; reset?: ResetTime; reason: string }

  // "En pause · 13 h 32" on the card; the reason says the rest.
  function chip(reset: ResetTime): string {
    if (!reset.clock) return m['arene.limits.picker.chipSoon']()
    return m[
      reset.clock.tomorrow ? 'arene.limits.picker.chipTomorrow' : 'arene.limits.picker.chip'
    ]({ time: TIME_SLOT })
  }

  function modelPause(id: string): Pause | undefined {
    const llm = paused.get(id)
    if (!llm) return undefined
    if (llm.reason === 'full') {
      return {
        chip: m['arene.limits.picker.fullBadge'](),
        icon: FULL_ICON,
        reason: m['arene.limits.picker.fullReason']()
      }
    }
    const reset = resetTime(llm.until)
    const reason = m[
      expensive?.scope === 'network'
        ? 'arene.limits.picker.pausedReasonNetwork'
        : 'arene.limits.picker.pausedReason'
    ]({ at: reset.at })
    return { chip: chip(reset), icon: PAUSED_ICON, reset, reason: spoken(reason, reset) }
  }

  function modePause(value: Mode): Pause | undefined {
    const pause = pausedModes.get(value)
    if (!pause) return undefined
    if (pause.full) {
      return {
        chip: m['arene.limits.picker.fullBadge'](),
        icon: FULL_ICON,
        reason: m['arene.limits.mode.reasonFull']()
      }
    }
    const reset = resetTime(pause.until)
    const reason = m['arene.limits.mode.reason']({ at: reset.at })
    return { chip: chip(reset), icon: PAUSED_ICON, reset, reason: spoken(reason, reset) }
  }

  // The line under the help text: how many cards are paused, how many full,
  // and why.
  const header = $derived.by(() => {
    const all = [...paused.values()]
    const count = all.filter((llm) => llm.reason === 'allowance').length
    const full = all.filter((llm) => llm.reason === 'full').length
    if (!expensive || !count) {
      if (!full) return undefined
      return {
        reset: resetTime(null),
        icon: FULL_ICON,
        text: m[full > 1 ? 'arene.limits.picker.onlyFullMany' : 'arene.limits.picker.onlyFullOne']({
          count: full
        }),
        why: m['arene.limits.picker.whyFull']()
      }
    }
    const reset = resetTime(expensive.resets_at)
    const network = expensive.scope === 'network'
    const key =
      count === 1
        ? network
          ? 'arene.limits.picker.headerOneNetwork'
          : 'arene.limits.picker.headerOne'
        : network
          ? 'arene.limits.picker.headerManyNetwork'
          : 'arene.limits.picker.headerMany'
    const pausedText = m[key]({ count, until: reset.until })
    const why = m[network ? 'arene.limits.picker.whyNetwork' : 'arene.limits.picker.why']()
    if (!full) return { reset, text: m['arene.limits.picker.header']({ paused: pausedText }), why }
    return {
      reset,
      text: m['arene.limits.picker.headerWithFull']({
        paused: pausedText,
        full: m[full > 1 ? 'arene.limits.picker.fullMany' : 'arene.limits.picker.fullOne']({
          count: full
        })
      }),
      why: `${why} ${m['arene.limits.picker.whyFull']()}`
    }
  })

  // The paused card last tapped, which then shows its reason.
  let triedMode = $state<Mode>()
  let triedModel = $state<string>()

  let neverClicked = $state(true)
  let showModelsSelection = $state(false)
  let search = $state('')

  const filteredModels = $derived.by(() => {
    const _search = search.toLowerCase()
    return models
      .filter((llm) => !_search || llm.search.includes(_search))
      .map((llm) => {
        const pause = modelPause(llm.id!)
        return { ...llm, label: llm.name, value: llm.id!, pause, disabledReason: pause?.reason }
      })
  })

  const modeChoices = $derived(
    getModeInfos().map((info) => {
      const pause = modePause(info.value)
      return { ...info, pause, disabledReason: pause?.reason }
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

{#snippet pauseChip(pause: Pause, tried: boolean)}
  <span class="mt-2 block">
    <Badge size="xs" class="cl-pause-chip">
      <Icon icon={pause.icon} size="xs" block class="me-1" />
      <!-- One flex item, so the space before the time stays. -->
      <span
        >{#if pause.reset}<TimedText
            text={pause.chip}
            reset={pause.reset}
          />{:else}{pause.chip}{/if}</span
      >
    </Badge>
  </span>
  {#if tried}
    <!-- Seen in the card; read out through the live region and the description. -->
    <span class="cl-selector__reason fr-text--sm mb-0! mt-2 block" aria-hidden="true">
      {pause.reason}
    </span>
  {/if}
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
                    {#if header}
                      <LimitHint id="picker-paused-hint" {...header} class="mt-2" />
                    {/if}
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
                bind:tried={triedMode}
                choices={modeChoices}
                containerClass="flex flex-col gap-3 md:gap-4"
                choiceClass="flex items-center p-4 text-sm text-dark-grey!"
                onChange={(mode) => (showModelsSelection = mode === 'custom')}
              >
                {#snippet option(opt, labelProps, input)}
                  <label {...labelProps}>
                    {@render input(opt, {
                      // A paused mode is not picked, so the dialog stays open.
                      'aria-controls':
                        opt.value != 'custom' && !opt.pause ? 'modal-mode-selection' : ''
                    })}
                    <Icon
                      icon={opt.icon}
                      block
                      class={['text-primary me-3', { 'cl-dimmed': !!opt.pause }]}
                    />
                    {#if opt.value != 'custom'}
                      <div>
                        <span>
                          <strong>{opt.label}</strong>&nbsp;: {opt.description}
                        </span>
                        {#if opt.pause}
                          {@render pauseChip(opt.pause, triedMode === opt.value)}
                        {/if}
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
                  label={m['arenaHome.compareModels.question']()}
                  bind:value={modelsSelection}
                  bind:tried={triedModel}
                  choices={filteredModels}
                  multiple
                  max={2}
                  containerClass="grid grid-cols-2 gap-3 md:grid-cols-3"
                  choiceClass="text-sm p-2 md:px-4 md:py-3"
                  onChange={toggleModelSelection}
                >
                  {#snippet option(opt, labelProps, input)}
                    {@const modelBadges = (['license', 'release', 'size'] as const)
                      .map((k) => opt.badges[k])
                      .filter((b) => !!b)}

                    <label {...labelProps}>
                      {@render input(opt)}
                      <!-- The logo and badges fade, the name keeps its contrast, and the
                           chip says it in words with an icon, not by colour alone. -->
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
                      <ul
                        class={[
                          'fr-badges-group mt-3! md:flex! hidden!',
                          { 'cl-dimmed': !!opt.pause }
                        ]}
                      >
                        {#each modelBadges as badge, i (i)}
                          <li>
                            <Badge {...badge} id="{opt.value}-card-badge-{i}" size="xs" noTooltip />
                          </li>
                        {/each}
                      </ul>
                      {#if opt.pause}
                        {@render pauseChip(opt.pause, triedModel === opt.value)}
                      {/if}
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

<style>
  /* Children's classes, so out of this component's scope. */
  #modal-mode-selection :global(.cl-dimmed) {
    opacity: 0.5;
    filter: grayscale(1);
  }

  #modal-mode-selection :global(.cl-pause-chip) {
    text-transform: none;
    font-weight: 500;
  }
</style>
