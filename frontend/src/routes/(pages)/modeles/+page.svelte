<script lang="ts">
  import { Accordion, AccordionGroup, Button, CheckboxGroup } from '$components/dsfr'
  import ModelInfoModal from '$components/ModelInfoModal.svelte'
  import ModelCard from '$lib/components/ModelCard.svelte'
  import SeoHead from '$lib/components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'
  import type { License, Organisation, Sizes } from '$lib/models'
  import { getModelsContext, SIZES } from '$lib/models'

  const models = getModelsContext()

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
  const filteredModels = $derived(
    models
      .filter((model) => {
        const sizeMatch = sizes.length === 0 || sizes.includes(model.friendly_size)
        const orgMatch = editors.length === 0 || editors.includes(model.organisation)
        const licenseMatch = licenses.length === 0 || licenses.includes(model.license)
        return sizeMatch && orgMatch && licenseMatch
      })
      .sort((a, b) => {
        switch (sortingMethod) {
          case 'date-desc':
            if (a.release_date && b.release_date && a.release_date !== b.release_date) {
              // @ts-ignore
              return new Date('01/' + b.release_date) - new Date('01/' + a.release_date)
            } else if (a.release_date) {
              return -1
            } else if (b.release_date) {
              return 1
            }
          case 'params-asc':
            if (a.params && b.params && a.params !== b.params) {
              return a.params - b.params
            }
          case 'org-asc':
            return a.organisation.localeCompare(b.organisation)
          default:
            return a.simple_name.localeCompare(b.simple_name)
        }
      })
  )

  const allFilter = $derived([editors, sizes, licenses])
  const filterCount = $derived(allFilter.reduce((acc, f) => acc + (f.length ? 1 : 0), 0))

  function resetFilters(e: MouseEvent) {
    e.preventDefault()
    allFilter.forEach((arr) => (arr.length = 0))
  }

  let selectedModel = $state<string>()
  const selectedModelData = $derived(models.find((m) => m.id === selectedModel))
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
          aria-expanded="true"
          aria-controls="fr-modal-filters-section"
          type="button"
          class="fr-sidemenu__btn"
        >
          {m['models.list.filters.display']()}
          {#if filterCount}
            <span class="fr-badge bg-primary! fr-badge--sm rounded-full! ms-2 text-white">
              {filterCount}
            </span>
          {/if}
        </button>
        <div class="fr-collapse" id="fr-modal-filters-section">
          <p class="fr-h5 mb-5! hidden md:block">
            {models.length}
            {m[`models.list.${models.length === 1 ? 'model' : 'models'}`]()}
          </p>
          <form class="mt-8 md:mt-0">
            <AccordionGroup class="mb-6">
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
                      <div class="text-(--grey-625-425) ms-auto text-sm">{option.count}</div>
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
                      <div class="text-(--grey-625-425) ms-auto text-sm">{option.count}</div>
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
                      <div class="text-(--grey-625-425) ms-auto text-sm">{option.count}</div>
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
        {models.length}
        {m[`models.list.${models.length === 1 ? 'model' : 'models'}`]()}
      </p>

      <div class="fr-select-group">
        <label class="fr-label" for="model-order">{m['models.list.triage.label']()}</label>
        <select
          class="fr-select w-auto!"
          id="model-order"
          bind:value={sortingMethod}
          name="model-order"
        >
          {#each sortingOptions as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </div>

      <div class="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
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
    padding: 0;
    margin: 0;
  }
</style>
