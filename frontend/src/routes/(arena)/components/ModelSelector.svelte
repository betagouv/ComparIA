<script lang="ts">
  import Dropdown from '$components/Dropdown.svelte'
  import { Badge, Button, Icon, Modal, Search } from '$components/dsfr'
  import { AILogo } from '$components/layout'
  import Selector from '$components/Selector.svelte'
  import type { APIModeAndPromptData } from '$lib/chatService.svelte'
  import { getModeInfos } from '$lib/chatService.svelte'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import type { BotModel } from '$lib/models'
  import { onMount } from 'svelte'

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

  let search = $state('')

  const filteredModels = $derived.by(() => {
    const _search = search.toLowerCase()
    return models
      .filter((llm) => !_search || llm.search.includes(_search))
      .map((llm) => ({
        ...llm,
        label: llm.name,
        value: llm.id!,
        disabled: llm.custom_selectable === false
      }))
  })

  const modeChoices = getModeInfos()
  const choice = $derived(modeChoices.find((c) => c.value === mode) || modeChoices[0])
  const { modelA, modelB } = $derived({
    modelA: models.find((model) => model.id === modelsSelection[0]),
    modelB: models.find((model) => model.id === modelsSelection[1])
  })

  // Closing the modal in manual mode with nothing picked would send two random
  // models labelled as a manual choice.
  onMount(() => {
    const el = document.getElementById('modal-models-selection')
    const fallBackToRandom = () => {
      if (mode !== 'custom' || modelsSelection.length) return
      mode = 'random'
      useToast(m['arenaHome.compareModels.noneSelected'](), 5000)
    }
    el?.addEventListener('dsfr.conceal', fallBackToRandom)
    return () => el?.removeEventListener('dsfr.conceal', fallBackToRandom)
  })

  function toggleModelSelection(): void {
    // If clicked on second model, close model selection modal
    if (modelsSelection.length === 2) {
      const modeSelectionModal = document.getElementById('modal-models-selection')
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
  <Dropdown
    id="dropdown-mode"
    label={choice.alt_label}
    title={m['arenaHome.selectModels.help']()}
    {disabled}
    closeOnSelect
    variant="light"
    buttonClass="fr-select text-sm! ps-3! cg-border shadow-none! rounded-lg! md:w-auto! w-full!"
  >
    {#snippet buttonLabel(label)}
      <Icon icon={choice.icon} size="sm" class="text-primary me-2" />
      <span class="label">{label}</span>
    {/snippet}

    <Selector
      id="mode-selector"
      kind="radio"
      label={m['arenaHome.selectModels.question']()}
      bind:value={mode}
      choices={modeChoices}
      checkedStyle="icon"
      containerClass="flex flex-col"
      choiceClass="flex items-center p-3 gap-3 text-sm text-dark-grey! bg-white"
    >
      {#snippet option(opt, labelProps, input)}
        <label {...labelProps}>
          {@render input(opt, {
            role: 'menuitem',
            'data-fr-opened': 'false',
            'aria-controls': opt.value === 'custom' ? 'modal-models-selection' : ''
          })}
          <Icon icon={opt.icon} block class="text-primary" />
          <div>
            <strong>{opt.label}</strong><br />
            {#if opt.value !== 'custom'}
              <span class="text-grey text-[11px]">{opt.description}</span>
            {/if}
          </div>
          {#if opt.value === 'custom'}
            <Icon icon="i-ri-arrow-right-s-line" block size="sm" class="ms-auto" />
          {:else if mode === opt.value}
            <Icon icon="i-ri-check-line" block size="md" class="text-primary ms-auto" />
          {/if}
        </label>
        <div class="not-last:b-b mx-3 border-[--grey-925-125]"></div>
      {/snippet}
    </Selector>
  </Dropdown>

  {#if mode == 'custom' && modelA}
    <Button
      variant="secondary"
      native
      aria-controls="modal-models-selection"
      {disabled}
      data-fr-opened="false"
      class="bg-white! px-3! text-sm! text-dark-grey! md:w-auto! xl:max-w-[260px] w-full! justify-start"
      style="--border-action-high-blue-france: var(--grey-925-125)"
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

<Modal
  id="modal-models-selection"
  titleId="modal-models-selection-title"
  sizeClass="fr-col-12 fr-col-md-10"
>
  <div class="mt-2 mb-8 w-full self-start">
    <div class="gap-3 md:flex-row flex w-full flex-col">
      <div>
        <h2 id="modal-models-selection-title" class="fr-h6 mb-3!">
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
  </div>
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
    choiceClass="cg-border text-sm p-2 md:px-4 md:py-3"
    onChange={toggleModelSelection}
  >
    {#snippet option(opt, labelProps, input)}
      {@const modelBadges = (['license', 'release', 'size'] as const)
        .map((k) => opt.badges[k])
        .filter((b) => !!b)}

      <label
        {...labelProps}
        class={[labelProps.class, { 'cursor-not-allowed opacity-60': opt.disabled }]}
      >
        {@render input(opt)}
        <div class="text-dark-grey flex">
          <AILogo
            logo={opt.lab.logo}
            customLogoId={opt.lab.has_custom_logo ? opt.lab.id : undefined}
            customLogoVersion={opt.lab.logo_version}
            alt=""
            class="me-2"
          />
          <span class="organisation md:inline hidden">{opt.lab.name}/</span><strong
            >{opt.name}</strong
          >
        </div>
        {#if opt.disabled}
          <p class="text-xs! mb-0! mt-2! text-grey">
            {m['arenaHome.compareModels.randomOnly']()}
          </p>
        {/if}
        <ul class="fr-badges-group mt-3! md:flex! hidden!">
          {#each modelBadges as badge, i (i)}
            <li>
              <Badge {...badge} id="{opt.value}-card-badge-{i}" size="xs" noTooltip />
            </li>
          {/each}
        </ul>
      </label>
    {/snippet}
  </Selector>

  {#snippet footer()}
    <div class="gap-4 md:flex-row flex w-full flex-col-reverse">
      <Button
        text={m['words.back']()}
        variant="tertiary"
        aria-controls="modal-models-selection"
        class="md:me-auto! md:w-auto! w-full!"
        icon="arrow-left-line"
      />

      <div class="gap-4 md:flex-row flex flex-col">
        <p class="mb-0! text-primary font-bold md:self-center">
          {m['arenaHome.compareModels.count']({ count: modelsSelection.length })}
        </p>

        <Button
          aria-controls="modal-models-selection"
          text={m['words.validate']()}
          disabled={!modelsSelection.length}
          class="md:w-auto! w-full!"
        />
      </div>
    </div>
  {/snippet}
</Modal>
