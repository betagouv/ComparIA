<script lang="ts">
  import { page } from '$app/state'
  import Dropdown from '$components/Dropdown.svelte'
  import { Button, CheckboxGroup, Search, Select } from '$components/dsfr'
  import ModelCard from '$components/ModelCard.svelte'
  import ModelInfoModal from '$components/ModelInfoModal.svelte'
  import PageLayout from '$components/PageLayout.svelte'
  import { SIZE_CLASSES } from '$lib/generated/constants'
  import { m } from '$lib/i18n/messages'
  import { getModelsContext, type BotModel } from '$lib/models'

  const { models, commons } = getModelsContext()

  const sortingOptions = (['name-asc', 'date-desc', 'params-asc', 'org-asc'] as const).map(
    (value) => ({
      value,
      label: m[`models.list.triage.options.${value}`]()
    })
  )

  let filters = $state<Record<(typeof filterDefs)[number]['id'], string[]>>({
    editors: [],
    sizes: [],
    licenses: [],
    statuses: ['enabled']
  })
  let sortingMethod = $state<'name-asc' | 'date-desc' | 'params-asc' | 'org-asc'>('name-asc')
  let search = $state('')

  const filterIncludes = <T extends string>(filter: T[], v: T) =>
    filter.length === 0 || filter.includes(v)

  const filterDefs = [
    {
      id: 'editors' as const,
      legend: m['models.list.filters.editor.legend'](),
      options: [
        { value: 'all', label: m['models.list.filters.editor.all'](), count: models.length },
        ...[...new Set(models.map((llm) => llm.lab.name))].sort().map((org) => ({
          value: org,
          count: models.filter((llm) => llm.lab.name === org).length
        }))
      ],
      match: (llm: BotModel) => filterIncludes(filters.editors, llm.lab.name),
      defaultValue: []
    },
    {
      id: 'sizes' as const,
      legend: m['models.list.filters.size.legend'](),
      options: [
        { value: 'all', label: m['models.list.filters.size.all'](), count: models.length },
        ...SIZE_CLASSES.map((value) => ({
          value,
          label: m[`models.list.filters.size.labels.${value}`](),
          count: models.filter((llm) => llm.size_class === value).length
        }))
      ],
      match: (llm: BotModel) => filterIncludes(filters.sizes, llm.size_class),
      defaultValue: []
    },
    {
      id: 'licenses' as const,
      legend: m['models.list.filters.license.legend'](),
      options: [
        { value: 'all', label: m['models.list.filters.license.all'](), count: models.length },
        ...[...new Set(models.map((llm) => llm.license.name))].map((license) => ({
          label:
            license === 'proprietary'
              ? m['models.licenses.type.proprietary']()
              : (license as string),
          value: license as string,
          count: models.filter((llm) => llm.license.name === license).length
        }))
      ],
      match: (llm: BotModel) => filterIncludes(filters.licenses, llm.license.name),
      defaultValue: []
    },
    {
      id: 'statuses' as const,
      legend: m['models.list.filters.statuses.legend'](),
      options: [
        { value: 'all', label: m['models.list.filters.statuses.all'](), count: models.length },
        {
          value: 'enabled',
          label: m['words.available'](),
          count: models.filter((llm) => llm.status === 'enabled').length
        },
        {
          value: 'archived',
          label: m['words.archived'](),
          count: models.filter((llm) => llm.status === 'archived').length
        },
        {
          value: 'new',
          label: m['words.new'](),
          count: models.filter((llm) => llm.new).length
        }
      ],
      match: (llm: BotModel) =>
        filterIncludes(filters.statuses, llm.status) ||
        (filters.statuses.includes('new') && llm.new),
      defaultValue: ['enabled']
    }
  ]

  const filteredModels = $derived.by(() => {
    const _search = search.toLowerCase()
    return models
      .filter((llm) => {
        const searchMatch = !_search || llm.search.includes(_search)
        const filtersMatch = filterDefs.every((f) => f.match(llm))
        return searchMatch && filtersMatch
      })
      .sort((a, b) => {
        switch (sortingMethod) {
          case 'date-desc':
            if (a.release_date !== b.release_date) {
              // @ts-expect-error date works
              return new Date(b.release_date) - new Date(a.release_date)
            } else if (a.release_date) {
              return -1
            } else if (b.release_date) {
              return 1
            }
          // falls through
          case 'params-asc':
            if (a.params && b.params && a.params !== b.params) {
              return a.params - b.params
            }
          // falls through
          case 'org-asc':
            return a.lab.name.localeCompare(b.lab.name)
          default:
            return a.name.localeCompare(b.name)
        }
      })
  })

  const hasFilters = $derived(
    filterDefs.some((f) => new Set(filters[f.id]).difference(new Set(f.defaultValue)).size)
  )

  function resetFilters(e: MouseEvent) {
    e.preventDefault()
    filterDefs.forEach((f) => (filters[f.id] = [...f.defaultValue]))
  }

  let selectedModel = $state<string>(page.url.hash.replace('#', ''))
  // human_id first: it is what goes in the URL, and it survives being shared
  // between environments, which the uuid does not. The uuid is still accepted
  // so links made while the card pointed at it keep working, and so the click
  // handlers, which pass an id, do not have to change.
  const selectedModelData = $derived(
    models.find((m) => m.human_id === selectedModel || m.id === selectedModel)
  )
</script>

<PageLayout
  seoTitle={m['seo.titles.modeles']()}
  title={m['seo.titles.modeles']()}
  titleAsBubble
  headerClass="sr-only!"
  class="py-0! px-0!"
>
  <aside class="bg-light-grey py-3 md:py-4 px-4 md:px-6">
    <form class="gap-3 lg:grid-cols-[280px_1fr] lg:items-start grid">
      <div>
        <Search
          id="model-list-search"
          bind:value={search}
          label={m['actions.searchModel']()}
          variant="light"
          class="w-full"
        />
      </div>

      <div class="gap-3 md:flex-row flex flex-col flex-wrap">
        {#each filterDefs as f (f.id)}
          <Dropdown id="dropdown-{f.id}" label={f.legend} variant="light" class="p-3">
            <CheckboxGroup {...f} bind:value={filters[f.id]} legendClass="sr-only" class="mb-0!">
              {#snippet labelSlot({ option })}
                <div class="flex w-full items-center justify-between">
                  <div class="me-4 whitespace-nowrap">
                    {#if f.id === 'sizes' && option.value !== 'all'}<strong>{option.value} :</strong
                      >{/if}
                    {'label' in option ? option.label : option.value}
                  </div>
                  <div class="text-sm text-[--grey-625-425]">
                    {option.count}
                  </div>
                </div>
              {/snippet}
            </CheckboxGroup>
          </Dropdown>
        {/each}

        {#if hasFilters}
          <div class="gap-3 md:flex-row md:items-center lg:shrink-0 flex flex-col">
            <Button
              icon="delete-line"
              size="sm"
              variant="tertiary"
              iconOnly
              title={m['models.list.filters.reset']()}
              aria-label={m['models.list.filters.reset']()}
              onclick={resetFilters}
              class="w-fit!"
            />
          </div>
        {/if}
      </div>
    </form>
  </aside>

  <div class="py-4 md:py-6 px-4 md:px-6">
    <!-- The live region wraps the heading rather than sitting on it: a role
         on the h2 would cost it its heading semantics. Filtering and searching
         change this count with no other signal. -->
    <div role="status" aria-live="polite">
      <h2 class="fr-h5 mb-4!">
        {filteredModels.length}
        {m[`models.list.${models.length === 1 ? 'model' : 'models'}`]()}
      </h2>
    </div>

    <Select
      bind:selected={sortingMethod}
      id="model-order"
      options={sortingOptions}
      label={m['models.list.triage.label']()}
      class="w-auto! max-w-full"
    />

    <ul class="gap-6 md:grid-cols-2 2xl:grid-cols-3 m-0! p-0! grid list-none">
      {#each filteredModels as model (model.id)}
        <li class="p-0! flex">
          <ModelCard
            {model}
            modalId="modal-model"
            {commons}
            onModelSelected={(name) => (selectedModel = name)}
          />
        </li>
      {/each}
    </ul>

    {#if filteredModels.length === 0}
      <p class="fr-text--lead fr-mt-4w" role="status">{m['models.list.noresults']()}</p>
    {/if}
  </div>
</PageLayout>

<ModelInfoModal
  model={selectedModelData}
  modalId="modal-model"
  {commons}
  autoOpen
  onClose={() => window.history.replaceState(null, '', page.url.pathname)}
/>

<style>
  :global(.fr-sidemenu .fr-collapse) {
    padding: 0 !important;
    margin: 0 !important;
  }
</style>
