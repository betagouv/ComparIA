<script lang="ts">
  import Dropdown from '$components/Dropdown.svelte'
  import { Badge, Button, Icon, Modal, Search } from '$components/dsfr'
  import { AILogo } from '$components/layout'
  import Selector from '$components/Selector.svelte'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import type { BotModel } from '$lib/models'
  import type { SelectionMode } from '$lib/selectionModes.svelte'

  let {
    models,
    modes,
    mode = $bindable(),
    modelsSelection = $bindable(),
    disabled = false
  }: {
    models: BotModel[]
    modes: SelectionMode[]
    mode: string
    modelsSelection: string[]
    disabled?: boolean
  } = $props()

  const modalId = 'modal-models-selection'

  let search = $state('')

  const choice = $derived(modes.find((c) => c.key === mode) ?? modes[0])
  const anyPicks = $derived(modes.some((c) => c.visitor_picks > 0))
  const modeChoices = $derived(modes.map((c) => ({ ...c, value: c.key })))

  // Only the models this mode lets the visitor pick.
  const pickableModels = $derived.by(() => {
    if (!choice.visitor_picks || !choice.llm_ids) return []
    const pool = new Set(choice.llm_ids)
    return models.filter((llm) => pool.has(llm.id!))
  })

  // A mode with two pools takes one pick from each: once a model is picked,
  // only models of the other pool may face it.
  const partners = $derived.by(() => {
    const [first] = modelsSelection
    if (modelsSelection.length !== 1 || !choice.llm_ids_a || !choice.llm_ids_b) return null
    return new Set([
      ...(choice.llm_ids_a.includes(first) ? choice.llm_ids_b : []),
      ...(choice.llm_ids_b.includes(first) ? choice.llm_ids_a : [])
    ])
  })

  const filteredModels = $derived.by(() => {
    const _search = search.toLowerCase()
    return pickableModels
      .filter((llm) => !_search || llm.search.includes(_search))
      .map((llm) => {
        const locked = llm.custom_selectable === false
        const unpairable =
          !!partners && !partners.has(llm.id!) && !modelsSelection.includes(llm.id!)
        return {
          ...llm,
          label: llm.name,
          value: llm.id!,
          locked,
          unpairable,
          disabled: locked || unpairable
        }
      })
  })

  const { modelA, modelB } = $derived({
    modelA: models.find((model) => model.id === modelsSelection[0]),
    modelB: models.find((model) => model.id === modelsSelection[1])
  })

  // The mode stays when nothing is picked, and both models are drawn from its
  // list: say so, since the visitor opened the picker to choose.
  function onModalClose() {
    if (choice.visitor_picks && !modelsSelection.length) {
      useToast(m['arenaHome.compareModels.noneSelected'](), 5000)
    }
  }

  function toggleModelSelection(): void {
    // Close the modal once the last model the mode allows is picked
    if (modelsSelection.length === choice.visitor_picks) {
      const modeSelectionModal = document.getElementById(modalId)
      if (modeSelectionModal) {
        window.setTimeout(() => {
          // @ts-expect-error - DSFR is globally available
          window.dsfr(modeSelectionModal).modal.conceal()
        }, 300)
      }
    }
  }
</script>

{#snippet picksSummary()}
  <Button
    variant="secondary"
    native
    aria-controls={modalId}
    {disabled}
    data-fr-opened="false"
    class="bg-white! px-3! text-sm! text-dark-grey! md:w-auto! xl:max-w-[260px] w-full! justify-start"
    style="--border-action-high-blue-france: var(--grey-925-125)"
  >
    {#if modelA}
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
    {:else}
      <Icon icon="i-ri-search-line" size="sm" class="text-primary me-2" />
      {m[
        choice.visitor_picks === 1
          ? 'arenaHome.compareModels.pickOne'
          : 'arenaHome.compareModels.pickTwo'
      ]()}
    {/if}
  </Button>
{/snippet}

<!-- Nothing to choose with a single blind mode: no empty box in the row either. -->
{#if modes.length > 1 || choice.visitor_picks}
  <div class="gap-3 md:col-span-5 md:flex-row flex flex-col">
    {#if modes.length > 1}
      <Dropdown
        id="dropdown-mode"
        label={choice.short_label}
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
                'aria-controls': opt.visitor_picks ? modalId : ''
              })}
              <Icon icon={opt.icon} block class="text-primary" />
              <div>
                <strong>{opt.label}</strong>
                {#if opt.description}
                  <br /><span class="text-grey text-[11px]">{opt.description}</span>
                {/if}
              </div>
              {#if opt.visitor_picks}
                <Icon icon="i-ri-arrow-right-s-line" block size="sm" class="ms-auto" />
              {:else if mode === opt.value}
                <Icon icon="i-ri-check-line" block size="md" class="text-primary ms-auto" />
              {/if}
            </label>
            <div class="not-last:b-b mx-3 border-[--grey-925-125]"></div>
          {/snippet}
        </Selector>
      </Dropdown>
    {/if}

    {#if choice.visitor_picks}
      {@render picksSummary()}
    {/if}
  </div>
{/if}

{#if anyPicks}
  <Modal
    id={modalId}
    titleId="{modalId}-title"
    sizeClass="fr-col-12 fr-col-md-10"
    onClose={onModalClose}
  >
    <div class="mt-2 mb-8 w-full self-start">
      <div class="gap-3 md:flex-row flex w-full flex-col">
        <div>
          <h2 id="{modalId}-title" class="fr-h6 mb-3!">
            {m['arenaHome.compareModels.question']()}
          </h2>
          <p class="mb-0!">
            {m[
              choice.visitor_picks === 1
                ? 'arenaHome.compareModels.helpOne'
                : 'arenaHome.compareModels.help'
            ]()}
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
      max={choice.visitor_picks}
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
          {#if opt.locked}
            <p class="text-xs! mb-0! mt-2! text-grey">
              {m['arenaHome.compareModels.randomOnly']()}
            </p>
          {:else if opt.unpairable}
            <p class="text-xs! mb-0! mt-2! text-grey">
              {m['arenaHome.compareModels.samePool']()}
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
          aria-controls={modalId}
          class="md:me-auto! md:w-auto! w-full!"
          icon="arrow-left-line"
        />

        <div class="gap-4 md:flex-row flex flex-col">
          <p class="mb-0! text-primary font-bold md:self-center">
            {m['arenaHome.compareModels.countMax']({
              count: modelsSelection.length,
              max: choice.visitor_picks
            })}
          </p>

          <Button
            aria-controls={modalId}
            text={m['words.validate']()}
            disabled={!modelsSelection.length}
            class="md:w-auto! w-full!"
          />
        </div>
      </div>
    {/snippet}
  </Modal>
{/if}
