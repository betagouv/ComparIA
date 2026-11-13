<script lang="ts">
  import { Accordion, Button, Segmented } from '$components/dsfr'
  import { ChipList, FormCheckboxGroup, FormInput, FormTagsInput } from '$components/form'
  import type { ModelFilter } from '$lib/generated/admin'
  import { ARCHS, ENERGY_CLASSES, MAYBE_ARCHS, SIZE_CLASSES } from '$lib/generated/constants'
  import { m } from '$lib/i18n/messages'
  import { tryI18n } from '$lib/utils/commons'
  import { clearCriterion, triState, type Catalogue } from '../filter'
  import { filterCriteria, inputLabel, type Lookups } from '../summary'
  import MultiSelect from './MultiSelect.svelte'

  let {
    id,
    value = $bindable(),
    catalogue,
    lookups,
    errors = {}
  }: {
    /** Also the prefix of the server's error keys: 'pool_a', 'pool_b'. */
    id: string
    value: ModelFilter
    catalogue: Catalogue
    lookups: Lookups
    errors?: Record<string, string>
  } = $props()

  const criteria = $derived(filterCriteria(value, lookups))
  const RARE: (keyof ModelFilter)[] = [
    'archs',
    'energy_classes',
    'inputs',
    'released_within_days',
    'released_after',
    'released_before',
    'price_out_max',
    'rate_limited',
    'top_ranked'
  ]
  const rareCount = $derived(
    criteria.filter((criterion) => criterion.fields.some((field) => RARE.includes(field))).length
  )

  const sizeHints: Record<(typeof SIZE_CLASSES)[number], () => string> = {
    XS: m['models.size.count.XS'],
    S: m['models.size.count.S'],
    M: m['models.size.count.M'],
    L: m['models.size.count.L'],
    XL: m['models.size.count.XL']
  }
  const sizeOptions = SIZE_CLASSES.map((size) => ({
    value: size,
    label: `${size} (${sizeHints[size]()})`
  }))
  const archOptions = [
    ...ARCHS.map((arch) => ({ value: arch, label: m[`generated.archs.${arch}.name`]() })),
    ...MAYBE_ARCHS.map((arch) => ({
      value: arch,
      label: m['admin.selectionModes.filter.maybeArch']({
        arch: m[`generated.archs.${arch.replace('maybe-', '') as (typeof ARCHS)[number]}.name`]()
      })
    }))
  ]
  const energyOptions = ENERGY_CLASSES.map((energy) => ({ value: energy, label: energy }))
  const inputOptions = (['text', 'image', 'audio', 'video'] as const).map((input) => ({
    value: input,
    label: inputLabel(input)
  }))
  const anyAll = [
    { value: 'any' as const, label: m['admin.selectionModes.filter.tagsAny']() },
    { value: 'all' as const, label: m['admin.selectionModes.filter.tagsAll']() }
  ]

  // Labels and help come from the schema's ModelFilter fields
  function label(field: keyof ModelFilter): string {
    return tryI18n(`selection_mode_upsert.ModelFilter.${field}.label`, field)!
  }

  function help(field: keyof ModelFilter): string | undefined {
    return tryI18n(`selection_mode_upsert.ModelFilter.${field}.help`)
  }

  function tri(yes: string, no: string) {
    return [
      { value: '', label: m['admin.selectionModes.filter.anyValue']() },
      { value: 'true', label: yes },
      { value: 'false', label: no }
    ]
  }

  function numberOrNull(input: unknown): number | null {
    if (input === '' || input === null || input === undefined) return null
    const number = Number(input)
    return Number.isNaN(number) ? null : number
  }

  // Every change hands the parent a new object, so it reacts whether or not
  // it passed a reactive one.
  function set<K extends keyof ModelFilter>(field: K, next: ModelFilter[K]) {
    value = { ...value, [field]: next }
  }

  function clear(fields: (keyof ModelFilter)[]) {
    value = clearCriterion(value, fields)
  }
</script>

{#snippet number(
  field: 'params_min' | 'params_max' | 'released_within_days' | 'price_out_max' | 'top_ranked',
  step = '1'
)}
  <FormInput
    id="{id}-{field}"
    label={label(field)}
    help={help(field)}
    type="number"
    {step}
    {errors}
    bind:value={() => value[field] ?? null, (input) => set(field, numberOrNull(input))}
  />
{/snippet}

<div class="filter-builder">
  <div class="mb-6 p-4 rounded-lg bg-[--background-alt-blue-france]">
    <p class="fr-text--sm font-bold mb-2!">{m['admin.selectionModes.filter.activeTitle']()}</p>
    {#if criteria.length}
      <ChipList
        label={m['admin.selectionModes.filter.activeTitle']()}
        items={criteria.map((criterion) => ({
          value: criterion.fields.join(','),
          label: criterion.text
        }))}
        onremove={(fields) => clear(fields.split(',') as (keyof ModelFilter)[])}
      />
    {:else}
      <p class="fr-text--sm mb-0!">{m['admin.selectionModes.filter.everyModel']()}</p>
    {/if}
  </div>

  <fieldset class="fr-fieldset filter-group">
    <legend class="fr-fieldset__legend">{m['admin.selectionModes.filter.groups.models']()}</legend>
    <div class="fr-fieldset__element">
      <MultiSelect
        id="{id}-llm_ids"
        label={label('llm_ids')}
        help={help('llm_ids')}
        choices={catalogue.llmChoices}
        {errors}
        bind:value={() => value.llm_ids, (next) => set('llm_ids', next)}
      />
      <MultiSelect
        id="{id}-exclude_llm_ids"
        label={label('exclude_llm_ids')}
        choices={catalogue.llmChoices}
        {errors}
        bind:value={() => value.exclude_llm_ids, (next) => set('exclude_llm_ids', next)}
      />
    </div>
  </fieldset>

  <fieldset class="fr-fieldset filter-group">
    <legend class="fr-fieldset__legend">{m['admin.selectionModes.filter.groups.labsTags']()}</legend
    >
    <div class="fr-fieldset__element md:grid-cols-2 md:gap-x-6 grid">
      <MultiSelect
        id="{id}-lab_ids"
        label={label('lab_ids')}
        choices={catalogue.labChoices}
        {errors}
        bind:value={() => value.lab_ids, (next) => set('lab_ids', next)}
      />
      <MultiSelect
        id="{id}-exclude_lab_ids"
        label={label('exclude_lab_ids')}
        choices={catalogue.labChoices}
        {errors}
        bind:value={() => value.exclude_lab_ids, (next) => set('exclude_lab_ids', next)}
      />
    </div>
    <div class="fr-fieldset__element">
      <FormTagsInput
        id="{id}-tags"
        label={label('tags')}
        help="{help('tags')} {catalogue.tags.length
          ? m['admin.selectionModes.filter.tagsInUse']({ tags: catalogue.tags.join(', ') })
          : m['admin.selectionModes.filter.tagsNone']()}"
        component="tags"
        suggestions={catalogue.tags}
        {errors}
        bind:value={() => value.tags, (next) => set('tags', next)}
      />
      {#if (value.tags?.length ?? 0) > 1}
        <Segmented
          id="{id}-tags_match"
          legend={label('tags_match')}
          options={anyAll}
          size="sm"
          class="mb-6!"
          bind:value={() => value.tags_match ?? 'any', (match) => set('tags_match', match)}
        />
      {/if}
      <Segmented
        id="{id}-arena_tools"
        legend={label('arena_tools')}
        options={tri(
          m['admin.selectionModes.filter.arenaToolsYes'](),
          m['admin.selectionModes.filter.arenaToolsNo']()
        )}
        size="sm"
        aria-describedby="{id}-arena_tools-help"
        bind:value={
          () => triState.toInput(value.arena_tools),
          (input) => set('arena_tools', triState.fromInput(input))
        }
      />
      <p id="{id}-arena_tools-help" class="fr-hint-text mt-2! mb-6!">
        {help('arena_tools')}
      </p>
      <FormTagsInput
        id="{id}-exclude_tags"
        label={label('exclude_tags')}
        component="tags"
        suggestions={catalogue.tags}
        {errors}
        bind:value={() => value.exclude_tags, (next) => set('exclude_tags', next)}
      />
    </div>
  </fieldset>

  <fieldset class="fr-fieldset filter-group">
    <legend class="fr-fieldset__legend">{m['admin.selectionModes.filter.groups.openness']()}</legend
    >
    <div class="fr-fieldset__element">
      <Segmented
        id="{id}-public_weights"
        legend={label('public_weights')}
        options={tri(
          m['admin.selectionModes.filter.openWeightsOnly'](),
          m['admin.selectionModes.filter.proprietaryOnly']()
        )}
        size="sm"
        class="mb-6!"
        bind:value={
          () => triState.toInput(value.public_weights),
          (input) => set('public_weights', triState.fromInput(input))
        }
      />
      <Segmented
        id="{id}-eu_hostable"
        legend={label('eu_hostable')}
        options={tri(m['words.yes'](), m['words.no']())}
        size="sm"
        class="mb-6!"
        bind:value={
          () => triState.toInput(value.eu_hostable),
          (input) => set('eu_hostable', triState.fromInput(input))
        }
      />
      <MultiSelect
        id="{id}-license_ids"
        label={label('license_ids')}
        choices={catalogue.licenseChoices}
        {errors}
        bind:value={() => value.license_ids, (next) => set('license_ids', next)}
      />
    </div>
  </fieldset>

  <fieldset class="fr-fieldset filter-group">
    <legend class="fr-fieldset__legend">{m['admin.selectionModes.filter.groups.size']()}</legend>
    <div class="fr-fieldset__element">
      <FormCheckboxGroup
        id="{id}-size_classes"
        label={label('size_classes')}
        help={help('size_classes')}
        options={sizeOptions}
        {errors}
        bind:value={
          () => value.size_classes as string[] | undefined,
          (next) => set('size_classes', next as ModelFilter['size_classes'])
        }
      />
    </div>
    <div class="fr-fieldset__element sm:grid-cols-2 sm:gap-x-6 grid">
      {@render number('params_min', 'any')}
      {@render number('params_max', 'any')}
    </div>
  </fieldset>

  <Accordion
    id="{id}-more"
    label={rareCount
      ? m['admin.selectionModes.filter.moreSet']({ count: rareCount })
      : m['admin.selectionModes.filter.more']()}
  >
    <FormCheckboxGroup
      id="{id}-archs"
      label={label('archs')}
      options={archOptions}
      {errors}
      bind:value={
        () => value.archs as string[] | undefined,
        (next) => set('archs', next as ModelFilter['archs'])
      }
    />
    <FormCheckboxGroup
      id="{id}-energy_classes"
      label={label('energy_classes')}
      help={help('energy_classes')}
      options={energyOptions}
      {errors}
      bind:value={
        () => value.energy_classes as string[] | undefined,
        (next) => set('energy_classes', next as ModelFilter['energy_classes'])
      }
    />
    <FormCheckboxGroup
      id="{id}-inputs"
      label={label('inputs')}
      help={help('inputs')}
      options={inputOptions}
      {errors}
      bind:value={
        () => value.inputs as string[] | undefined,
        (next) => set('inputs', next as ModelFilter['inputs'])
      }
    />

    <div class="sm:grid-cols-3 sm:gap-x-6 grid">
      {@render number('released_within_days')}
      <FormInput
        id="{id}-released_after"
        label={label('released_after')}
        type="date"
        {errors}
        bind:value={
          () => value.released_after ?? '',
          (date) => set('released_after', (date as string) || null)
        }
      />
      <FormInput
        id="{id}-released_before"
        label={label('released_before')}
        type="date"
        {errors}
        bind:value={
          () => value.released_before ?? '',
          (date) => set('released_before', (date as string) || null)
        }
      />
    </div>

    <div class="sm:grid-cols-2 sm:gap-x-6 grid">
      {@render number('price_out_max', 'any')}
      {@render number('top_ranked')}
    </div>

    <Segmented
      id="{id}-rate_limited"
      legend={label('rate_limited')}
      options={tri(
        m['admin.selectionModes.filter.rateLimitedOnly'](),
        m['admin.selectionModes.filter.rateLimitedNone']()
      )}
      size="sm"
      bind:value={
        () => triState.toInput(value.rate_limited),
        (input) => set('rate_limited', triState.fromInput(input))
      }
    />
    <p class="fr-hint-text mt-2!">{help('rate_limited')}</p>
  </Accordion>

  {#if criteria.length}
    <Button
      size="sm"
      variant="tertiary-no-outline"
      icon="close-circle-line"
      class="mt-4"
      text={m['admin.selectionModes.filter.clearAll']()}
      onclick={() => (value = {})}
    />
  {/if}
</div>

<style>
  .filter-group {
    margin-bottom: 0.5rem;
  }

  .filter-group :global(.fr-segmented) {
    max-width: 100%;
    overflow-x: auto;
  }
</style>
