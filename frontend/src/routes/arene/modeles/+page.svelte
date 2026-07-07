<script lang="ts">
  import { page } from '$app/state'
  import Dropdown from '$components/Dropdown.svelte'
  import { Button, CheckboxGroup, Search, Select } from '$components/dsfr'
  import ModelCard from '$components/ModelCard.svelte'
  import ModelInfoModal from '$components/ModelInfoModal.svelte'
  import PageLayout from '$components/PageLayout.svelte'
  import { SIZE_CLASSES, type SizeClasses } from '$lib/generated/constants'
  import { m } from '$lib/i18n/messages'
  import { getModelsContext } from '$lib/models'

  const { models, commons } = getModelsContext()

  const editorFilter = {
    id: 'editor',
    legend: m['models.list.filters.editor.legend'](),
    options: [
      { value: 'all', label: m['models.list.filters.editor.all'](), count: models.length },
      ...[...new Set(models.map((llm) => llm.lab.name))]
        .sort()
        .map((org) => ({ value: org, count: models.filter((llm) => llm.lab.name === org).length }))
    ]
  }

  const sizeFilter = {
    id: 'size',
    legend: m['models.list.filters.size.legend'](),
    options: [
      { value: 'all', label: m['models.list.filters.size.all'](), count: models.length },
      ...SIZE_CLASSES.map((value) => ({
        value,
        label: m[`models.list.filters.size.labels.${value}`](),
        count: models.filter((llm) => llm.size_class === value).length
      }))
    ]
  }

  const licenseFilter = {
    id: 'license',
    legend: m['models.list.filters.license.legend'](),
    options: [
      { value: 'all', label: m['models.list.filters.license.all'](), count: models.length },
      ...[...new Set(models.map((llm) => llm.license.name))].map((license) => ({
        label:
          license === 'proprietary' ? m['models.licenses.type.proprietary']() : (license as string),
        value: license as string,
        count: models.filter((llm) => llm.license.name === license).length
      }))
    ]
  }

  const statusesFilter = {
    id: 'statuses',
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
    ]
  }

  const sortingOptions = (['name-asc', 'date-desc', 'params-asc', 'org-asc'] as const).map(
    (value) => ({
      value,
      label: m[`models.list.triage.options.${value}`]()
    })
  )

  let editors = $state<string[]>([])
  let sizes = $state<SizeClasses[]>([])
  let licenses = $state<string[]>([])
  let statuses = $state<string[]>(['enabled'])
  let sortingMethod = $state<'name-asc' | 'date-desc' | 'params-asc' | 'org-asc'>('name-asc')
  let search = $state('')

  const filteredModels = $derived.by(() => {
    const _search = search.toLowerCase()
    return models
      .filter((model) => {
        const searchMatch = !_search || model.search.includes(_search)
        const sizeMatch = sizes.length === 0 || sizes.includes(model.size_class)
        const orgMatch = editors.length === 0 || editors.includes(model.lab.name)
        const licenseMatch = licenses.length === 0 || licenses.includes(model.license.name)
        const statusMatch =
          statuses.length === 0 ||
          statuses.includes(model.status) ||
          (statuses.includes('new') && model.new)
        return searchMatch && sizeMatch && orgMatch && licenseMatch && statusMatch
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

  const allFilter = $derived([editors, sizes, licenses])
  const archivedIsDefault = $derived(statuses.length === 1 && statuses[0] === 'enabled')
  const filterCount = $derived(
    allFilter.reduce((acc, f) => acc + (f.length ? 1 : 0), 0) + (archivedIsDefault ? 0 : 1)
  )

  function resetFilters(e: MouseEvent) {
    e.preventDefault()
    editors.length = 0
    sizes.length = 0
    licenses.length = 0
    statuses = ['enabled']
  }

  let selectedModel = $state<string>(page.url.hash.replace('#', ''))
  const selectedModelData = $derived(models.find((m) => m.id === selectedModel))
</script>

<PageLayout
  seoTitle={m['seo.titles.modeles']()}
  title={m['seo.titles.modeles']()}
  titleAsBubble
  headerClass="hidden"
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
        <Dropdown id="dropdown-editors" label={editorFilter.legend} variant="light">
          <CheckboxGroup
            {...editorFilter}
            bind:value={editors}
            legendClass="sr-only"
            class="mb-0! md:w-max"
          >
            {#snippet labelSlot({ option })}
              <div class="me-4">{'label' in option ? option.label : option.value}</div>
              <div class="text-sm ms-auto text-[--grey-625-425]">
                {option.value === 'all' ? models.length : option.count}
              </div>
            {/snippet}
          </CheckboxGroup>
        </Dropdown>

        <Dropdown id="dropdown-size" label={sizeFilter.legend} variant="light">
          <CheckboxGroup
            {...sizeFilter}
            bind:value={sizes}
            legendClass="sr-only"
            class="mb-0! md:w-max"
          >
            {#snippet labelSlot({ option })}
              <div class="me-4">
                {#if option.value !== 'all'}<strong>{option.value} :</strong>{/if}
                {option.label}
              </div>
              <div class="text-sm ms-auto text-[--grey-625-425]">{option.count}</div>
            {/snippet}
          </CheckboxGroup>
        </Dropdown>

        <Dropdown id="dropdown-license" label={licenseFilter.legend} variant="light">
          <CheckboxGroup
            {...licenseFilter}
            bind:value={licenses}
            legendClass="sr-only"
            class="mb-0! md:w-max"
          >
            {#snippet labelSlot({ option })}
              <div class="me-4">{option.label}</div>
              <div class="text-sm ms-auto text-[--grey-625-425]">{option.count}</div>
            {/snippet}
          </CheckboxGroup>
        </Dropdown>

        <Dropdown id="dropdown-statuses" label={statusesFilter.legend} variant="light">
          <CheckboxGroup
            {...statusesFilter}
            bind:value={statuses}
            legendClass="sr-only"
            class="mb-0! md:w-max"
          >
            {#snippet labelSlot({ option })}
              <div class="me-4">{option.label}</div>
              <div class="text-sm ms-auto text-[--grey-625-425]">{option.count}</div>
            {/snippet}
          </CheckboxGroup>
        </Dropdown>

        {#if filterCount > 0}
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
    <p class="fr-h5 mb-4!">
      {filteredModels.length}
      {m[`models.list.${models.length === 1 ? 'model' : 'models'}`]()}
    </p>

    <Select
      bind:selected={sortingMethod}
      id="model-order"
      options={sortingOptions}
      label={m['models.list.triage.label']()}
      class="w-auto! max-w-full"
    />

    <div class="gap-6 md:grid-cols-2 xl:grid-cols-3 grid">
      {#each filteredModels as model (model.id)}
        <ModelCard
          {model}
          modalId="modal-model"
          {commons}
          onModelSelected={(name) => (selectedModel = name)}
        />
      {/each}
    </div>

    {#if filteredModels.length === 0}
      <p class="fr-text--lead fr-mt-4w">{m['models.list.noresults']()}</p>
    {/if}
  </div>
</PageLayout>

<ModelInfoModal
  model={selectedModelData}
  modalId="modal-model"
  {commons}
  onClose={() => window.history.replaceState(null, '', page.url.pathname)}
/>

<style>
  :global(.fr-sidemenu .fr-collapse) {
    padding: 0 !important;
    margin: 0 !important;
  }
</style>
