<script lang="ts">
  import {
    Accordion,
    AccordionGroup,
    Button,
    CheckboxGroup,
    Search,
    Toggle
  } from '$components/dsfr'
  import ModelCard from '$components/ModelCard.svelte'
  import ModelInfoModal from '$components/ModelInfoModal.svelte'
  import SeoHead from '$components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'
  import type { License, Organisation, Sizes } from '$lib/models'
  import { getModelsContext, SIZES } from '$lib/models'
  import { onMount } from 'svelte'

  const models = getModelsContext().models

  const editorFilter = {
    id: 'editor',
    legend: m['models.list.filters.editor.legend'](),
    options: [...new Set(models.map((m) => m.organisation))]
      .sort()
      .map((org) => ({ value: org, count: models.filter((m) => m.organisation === org).length }))
  }

  const sizeFilter = {
    id: 'size',
    legend: m['models.list.filters.size.legend'](),
    options: SIZES.map((value) => ({
      value,
      label: m[`models.list.filters.size.labels.${value}`](),
      count: models.filter((m) => m.friendly_size === value).length
    }))
  }

  const licenseFilter = {
    id: 'license',
    legend: m['models.list.filters.license.legend'](),
    options: [...new Set(models.map((m) => m.license))].map((license) => ({
      label:
        license === 'proprietary' ? m['models.licenses.type.proprietary']() : (license as string),
      value: license as string,
      count: models.filter((m) => m.license === license).length
    }))
  }

  const sortingOptions = (['name-asc', 'date-desc', 'params-asc', 'org-asc'] as const).map(
    (value) => ({
      value,
      label: m[`models.list.triage.options.${value}`]()
    })
  )

  let editors = $state<Organisation[]>([])
  let sizes = $state<Sizes[]>([])
  let licenses = $state<License[]>([])
  let sortingMethod = $state<'name-asc' | 'date-desc' | 'params-asc' | 'org-asc'>('name-asc')
  let showArchived = $state(false)
  let search = $state('')

  const filteredModels = $derived.by(() => {
    const _search = search.toLowerCase()
    return models
      .filter((model) => {
        const searchMatch = !_search || model.search.includes(_search)
        const sizeMatch = sizes.length === 0 || sizes.includes(model.friendly_size)
        const orgMatch = editors.length === 0 || editors.includes(model.organisation)
        const licenseMatch = licenses.length === 0 || licenses.includes(model.license)
        const archivedMatch = model.status === 'enabled' || showArchived
        return searchMatch && sizeMatch && orgMatch && licenseMatch && archivedMatch
      })
      .sort((a, b) => {
        switch (sortingMethod) {
          case 'date-desc':
            if (a.release_date && b.release_date && a.release_date !== b.release_date) {
              // @ts-expect-error date works
              return new Date('01/' + b.release_date) - new Date('01/' + a.release_date)
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
            return a.organisation.localeCompare(b.organisation)
          default:
            return a.simple_name.localeCompare(b.simple_name)
        }
      })
  })

  const allFilter = $derived([editors, sizes, licenses])
  const filterCount = $derived(allFilter.reduce((acc, f) => acc + (f.length ? 1 : 0), 0))

  function resetFilters(e: MouseEvent) {
    e.preventDefault()
    allFilter.forEach((arr) => (arr.length = 0))
  }

  let selectedModel = $state<string>()
  const selectedModelData = $derived(models.find((m) => m.id === selectedModel))

  onMount(() => {
    const hash = window.location.hash.slice(1)
    if (hash) {
      const model = models.find((m) => m.id === hash)
      if (model) {
        selectedModel = model.id
        const modalElement = document.getElementById('modal-model')
        if (modalElement) {
          window.setTimeout(() => {
            // @ts-expect-error - DSFR is globally available
            window.dsfr(modalElement).modal.disclose()
            // Restore the hash in the URL (DSFR removes it when opening the modal)
            window.history.replaceState(null, '', `#${hash}`)
          }, 100)
        }
      } else {
        // Keep the hash in the URL even if the model is not found
        window.history.replaceState(null, '', `#${hash}`)
      }
    }

    // Remove hash from URL when modal is closed
    const modalElement = document.getElementById('modal-model')
    if (modalElement) {
      modalElement.addEventListener('dsfr.conceal', () => {
        window.history.replaceState(null, '', window.location.pathname)
      })
    }
  })
</script>

<SeoHead title={m['seo.titles.modeles']()} />

<main>
  <div class="fr-container pb-10 md:flex md:flex-row md:py-10">
    <aside
      class="fr-sidemenu mb-5 md:mb-0 md:basis-1/3"
      role="navigation"
      aria-labelledby="sidemenu-title"
    >
      <div class="fr-sidemenu__inner h-full">
        <button
          id="results-count"
          aria-expanded="false"
          aria-controls="fr-modal-filters-section"
          type="button"
          class="fr-sidemenu__btn"
        >
          {m['models.list.filters.display']()}
          {#if filterCount}
            <span class="fr-badge fr-badge--sm bg-primary! text-white! ms-2 rounded-full!">
              {filterCount}
            </span>
          {/if}
        </button>
        <div class="fr-collapse" id="fr-modal-filters-section">
          <p class="fr-h5 -mt-4! mb-5! md:block hidden">
            {filteredModels.length}
            {m[`models.list.${models.length === 1 ? 'model' : 'models'}`]()}
          </p>
          <form class="mt-8 md:mt-0">
            <Search
              id="model-list-search"
              bind:value={search}
              label={m['actions.searchModel']()}
              class="md:flex! mb-7 hidden!"
            />

            <Toggle
              id="archived"
              bind:value={showArchived}
              label={m['models.list.filters.archived.label']()}
              help={m['models.list.filters.archived.help']()}
              checkedLabel={m['models.list.filters.archived.checkedLabel']()}
              uncheckedLabel={m['models.list.filters.archived.uncheckedLabel']()}
              groupClass="mx-4 md:mx-0"
            />

            <AccordionGroup class="mb-6 mt-6">
              <Accordion id="field-editors" label={editorFilter.legend}>
                <div class="p-4">
                  <CheckboxGroup
                    {...editorFilter}
                    bind:value={editors}
                    legendClass="sr-only"
                    labelClass="flex-nowrap!"
                    class="mb-0!"
                  >
                    {#snippet labelSlot({ option })}
                      <div class="me-2">{option.value}</div>
                      <div class="text-sm ms-auto text-[--grey-625-425]">{option.count}</div>
                    {/snippet}
                  </CheckboxGroup>
                </div>
              </Accordion>

              <Accordion id="field-size" label={sizeFilter.legend}>
                <div class="p-4">
                  <CheckboxGroup
                    {...sizeFilter}
                    bind:value={sizes}
                    legendClass="sr-only"
                    labelClass="flex-nowrap!"
                    class="mb-0!"
                  >
                    {#snippet labelSlot({ option })}
                      <div class="me-2"><strong>{option.value} :</strong> {option.label}</div>
                      <div class="text-sm ms-auto text-[--grey-625-425]">{option.count}</div>
                    {/snippet}
                  </CheckboxGroup>
                </div>
              </Accordion>

              <Accordion id="field-license" label={licenseFilter.legend}>
                <div class="p-4">
                  <CheckboxGroup
                    {...licenseFilter}
                    bind:value={licenses}
                    legendClass="sr-only"
                    labelClass="flex-nowrap!"
                    class="mb-0!"
                  >
                    {#snippet labelSlot({ option })}
                      <div class="me-2">{option.label}</div>
                      <div class="text-sm ms-auto text-[--grey-625-425]">{option.count}</div>
                    {/snippet}
                  </CheckboxGroup>
                </div>
              </Accordion>
            </AccordionGroup>

            <div class="mb-8">
              <Button
                text={m['models.list.filters.reset']()}
                icon="delete-line"
                variant="tertiary-no-outline"
                disabled={filterCount === 0}
                onclick={resetFilters}
              />
            </div>
          </form>
        </div>
      </div>
    </aside>

    <div class="basis-full">
      <!-- <h2 class="fr-h2">{m['models.list.title']()}</h2>
      <p class="fr-text--lead">{m['models.list.intro']()}</p> -->

      <p class="fr-h6 mb-4! md:hidden">
        {filteredModels.length}
        {m[`models.list.${models.length === 1 ? 'model' : 'models'}`]()}
      </p>

      <Search
        id="model-list-search"
        bind:value={search}
        label={m['actions.searchModel']()}
        class="md:hidden! mb-4"
      />

      <div class="fr-select-group">
        <label class="fr-label" for="model-order">{m['models.list.triage.label']()}</label>
        <select
          id="model-order"
          bind:value={sortingMethod}
          name="model-order"
          class="fr-select w-auto! max-w-full"
        >
          {#each sortingOptions as option (option.value)}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </div>

      <div class="gap-6 md:grid-cols-2 xl:grid-cols-3 grid">
        {#each filteredModels as model (model.id)}
          <ModelCard
            {model}
            modalId="modal-model"
            onModelSelected={(name) => (selectedModel = name)}
          />
        {/each}
      </div>

      {#if filteredModels.length === 0}
        <p class="fr-text--lead fr-mt-4w">{m['models.list.noresults']()}</p>
      {/if}
    </div>
  </div>
</main>

<ModelInfoModal model={selectedModelData} modalId="modal-model" />

<style>
  :global(.fr-sidemenu .fr-collapse) {
    padding: 0 !important;
    margin: 0 !important;
  }
</style>
