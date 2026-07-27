<script lang="ts">
  import { goto, invalidate } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import { Badge, Button, Icon, Modal, Pagination, Select, Table } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { api } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import type { OrderingMethod, TableCol } from '$lib/utils/data'
  import { sortRows, toSearchString } from '$lib/utils/data'
  import { SvelteURLSearchParams } from 'svelte/reactivity'
  import type { PageProps } from './$types'
  import type { PromptSuggestion, SuggestionStatus } from './types'

  let { data }: PageProps = $props()

  const refetch = () => invalidate('admin:suggestions')
  const baseRoute = '/admin/suggestions'

  // These local controls are deliberately initialized from the SSR-loaded data,
  // then resynchronized below whenever SvelteKit refreshes the page data.
  // svelte-ignore state_referenced_locally
  let search = $state(data.filters.search)
  // svelte-ignore state_referenced_locally
  let status = $state(data.filters.status)
  // svelte-ignore state_referenced_locally
  let locale = $state(data.filters.locale)
  // svelte-ignore state_referenced_locally
  let categoryId = $state(data.filters.category_id)
  // svelte-ignore state_referenced_locally
  let currentPage = $state(data.suggestions.page - 1)

  let suggestionToToggle = $state<PromptSuggestion | null>(null)
  let actionLoading = $state(false)
  let prompt = $state('')
  let promptCategoryId = $state('')
  let promptLocale = $state('fr')
  let formError = $state<string>()
  let formLoading = $state(false)
  let categoryLocale = $state('fr')
  let categoryTitle = $state('')
  let categoryDescription = $state('')
  let categoryIcon = $state('i-ri-lightbulb-line')
  let categoryTooltip = $state('')
  let categoryFormError = $state<string>()
  let categoryFormLoading = $state(false)

  const categories = $derived(data.suggestions.categories)
  const supportedLocales = ['fr', 'da', 'sv']
  const availableLocales = $derived(
    [...new Set(categories.map((category) => category.locale))].sort()
  )
  const filterCategoryOptions = $derived([
    { value: '', label: m['admin.suggestions.allCategories']() },
    ...categories
      .filter((category) => !locale || category.locale === locale)
      .map((category) => ({ value: category.id, label: category.title }))
  ])
  const promptCategoryOptions = $derived([
    { value: '', label: m['admin.suggestions.category']() },
    ...categories
      .filter((category) => category.locale === promptLocale)
      .map((category) => ({ value: category.id, label: category.title }))
  ])
  const localeOptions = $derived([
    { value: '', label: m['admin.suggestions.allLocales']() },
    ...availableLocales.map((value) => ({ value, label: value.toUpperCase() }))
  ])
  const promptLocaleOptions = $derived(
    availableLocales.map((value) => ({ value, label: value.toUpperCase() }))
  )
  const categoryLocaleOptions = supportedLocales.map((value) => ({
    value,
    label: value.toUpperCase()
  }))
  const categoryIconOptions = [
    { value: 'i-ri-lightbulb-line', label: m['admin.suggestions.iconLightbulb']() },
    { value: 'i-ri-draft-line', label: m['admin.suggestions.iconDocument']() },
    { value: 'i-ri-question-answer-line', label: m['admin.suggestions.iconDiscussion']() },
    { value: 'i-ri-book-open-line', label: m['admin.suggestions.iconBook']() },
    { value: 'i-ri-flask-line', label: m['admin.suggestions.iconScience']() },
    { value: 'i-ri-translate-2', label: m['admin.suggestions.iconTranslation']() },
    { value: 'i-ri-restaurant-line', label: m['admin.suggestions.iconFood']() },
    { value: 'i-ri-magic-line', label: m['admin.suggestions.iconCreative']() }
  ]
  const statusOptions: { value: '' | SuggestionStatus; label: string }[] = [
    { value: '', label: m['admin.suggestions.allStatuses']() },
    { value: 'available', label: m['admin.suggestions.available']() },
    { value: 'archived', label: m['admin.suggestions.archived']() }
  ]

  const rows = $derived(
    data.suggestions.items.map((suggestion) => ({
      ...suggestion,
      id: suggestion.id,
      search: toSearchString([suggestion.text, suggestion.category_title, suggestion.locale]),
      actions: undefined
    }))
  )
  type SuggestionColumn = 'text' | 'category_title' | 'locale' | 'status' | 'actions'
  const cols = [
    { id: 'text', label: m['admin.suggestions.prompt'](), orderable: true },
    { id: 'category_title', label: m['admin.suggestions.category'](), orderable: true },
    { id: 'locale', label: m['admin.suggestions.locale'](), orderable: true },
    { id: 'status', label: m['admin.suggestions.status'](), orderable: true },
    { id: 'actions', label: m['admin.suggestions.actions']() }
  ] satisfies TableCol<SuggestionColumn>[]
  type ColKey = (typeof cols)[number]['id']

  let orderingCol = $state<ColKey>('text')
  let orderingMethod = $state<OrderingMethod>('ascending')
  const sortedRows = $derived(
    sortRows(rows, cols, { col: orderingCol, method: orderingMethod, search: '' })
  )

  $effect(() => {
    search = data.filters.search
    status = data.filters.status
    locale = data.filters.locale
    categoryId = data.filters.category_id
    currentPage = data.suggestions.page - 1
  })

  $effect(() => {
    if (search === data.filters.search) return

    const timeout = setTimeout(() => updateQuery({ search, page: '1' }), 300)
    return () => clearTimeout(timeout)
  })

  $effect(() => {
    if (currentPage === data.suggestions.page - 1) return
    updateQuery({ page: String(currentPage + 1) })
  })

  function updateQuery(updates: Record<string, string>) {
    const params = new SvelteURLSearchParams(page.url.searchParams)

    for (const [key, value] of Object.entries(updates)) {
      if (value) params.set(key, value)
      else params.delete(key)
    }

    goto(resolve(`${baseRoute}?${params.toString()}`))
  }

  function updateFilters() {
    updateQuery({ status, locale, category_id: categoryId, page: '1' })
  }

  function updateLocaleFilter() {
    if (
      categoryId &&
      !categories.some((category) => category.id === categoryId && category.locale === locale)
    ) {
      categoryId = ''
    }
    updateFilters()
  }

  function openAddModal() {
    prompt = ''
    formError = undefined
    promptLocale = availableLocales.includes('fr') ? 'fr' : (availableLocales[0] ?? 'fr')
    promptCategoryId = ''
    discloseModal('fr-modal-add-suggestion')
  }

  function openStatusModal(suggestion: PromptSuggestion) {
    suggestionToToggle = suggestion
    discloseModal('fr-modal-suggestion-status')
  }

  function openAddCategoryModal() {
    categoryLocale = 'fr'
    categoryTitle = ''
    categoryDescription = ''
    categoryIcon = 'i-ri-lightbulb-line'
    categoryTooltip = ''
    categoryFormError = undefined
    discloseModal('fr-modal-add-suggestion-category')
  }

  function discloseModal(id: string) {
    const element = document.getElementById(id)
    if (element) {
      // @ts-expect-error - DSFR is globally available
      window.dsfr(element).modal.disclose()
    }
  }

  function closeModal(id: string) {
    const element = document.getElementById(id)
    if (element) {
      // @ts-expect-error - DSFR is globally available
      window.dsfr(element).modal.conceal()
    }
  }

  async function createSuggestion(event: SubmitEvent) {
    event.preventDefault()
    const text = prompt.trim()
    if (!text || !promptCategoryId) {
      formError = m['admin.suggestions.validation']()
      return
    }

    formLoading = true
    formError = undefined
    try {
      await api.request('/admin/suggestions', {
        method: 'POST',
        body: JSON.stringify({ text, category_id: promptCategoryId })
      })
      closeModal('fr-modal-add-suggestion')
      useToast(m['admin.suggestions.createSuccess'](), 4000)
      await refetch()
    } catch (error) {
      const message = (error as Error).message
      formError = message.includes('409') ? m['admin.suggestions.duplicateError']() : message
    } finally {
      formLoading = false
    }
  }

  async function createCategory(event: SubmitEvent) {
    event.preventDefault()
    const title = categoryTitle.trim()
    const description = categoryDescription.trim()
    const tooltip = categoryTooltip.trim()
    if (!title || !description || !categoryIcon) {
      categoryFormError = m['admin.suggestions.categoryValidation']()
      return
    }

    categoryFormLoading = true
    categoryFormError = undefined
    try {
      await api.request('/admin/suggestions/categories', {
        method: 'POST',
        body: JSON.stringify({
          locale: categoryLocale,
          title,
          description,
          icon: categoryIcon,
          tooltip: tooltip || null
        })
      })
      closeModal('fr-modal-add-suggestion-category')
      useToast(m['admin.suggestions.categoryCreateSuccess'](), 4000)
      await refetch()
    } catch (error) {
      const message = (error as Error).message
      categoryFormError = message.includes('409')
        ? m['admin.suggestions.categoryDuplicateError']()
        : message
    } finally {
      categoryFormLoading = false
    }
  }

  async function confirmStatusChange() {
    if (!suggestionToToggle) return

    actionLoading = true
    const archive = suggestionToToggle.status !== 'archived'
    try {
      await api.request(`/admin/suggestions/${suggestionToToggle.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ archived: archive })
      })
      closeModal('fr-modal-suggestion-status')
      useToast(
        archive ? m['admin.suggestions.archiveSuccess']() : m['admin.suggestions.restoreSuccess'](),
        4000
      )
      await refetch()
    } catch (error) {
      useToast((error as Error).message, 6000, 'error')
    } finally {
      actionLoading = false
    }
  }

  function statusLabel(value: SuggestionStatus) {
    return value === 'archived'
      ? m['admin.suggestions.archived']()
      : m['admin.suggestions.available']()
  }
</script>

<PageLayout
  seoTitle={m['admin.suggestions.title']()}
  title={m['admin.suggestions.title']()}
  subtitle={m['admin.suggestions.subtitle']()}
>
  <Table
    bind:search
    bind:orderingMethod
    bind:orderingCol
    caption={m['admin.suggestions.tableCaption']()}
    hideCaption
    {cols}
    rows={sortedRows}
    searchLabel={m['words.search']()}
  >
    {#snippet headerLeft()}
      <fieldset class="fr-fieldset mb-0!">
        <legend class="fr-fieldset__legend--regular fr-text--sm mb-2!">
          {m['admin.suggestions.filters']()}
        </legend>
        <div class="gap-3 md:flex-row flex flex-col">
          <Select
            id="suggestions-status-filter"
            label={m['admin.suggestions.status']()}
            options={statusOptions}
            bind:selected={status}
            onchange={updateFilters}
          />
          <Select
            id="suggestions-locale-filter"
            label={m['admin.suggestions.locale']()}
            options={localeOptions}
            bind:selected={locale}
            onchange={updateLocaleFilter}
          />
          <Select
            id="suggestions-category-filter"
            label={m['admin.suggestions.category']()}
            options={filterCategoryOptions}
            bind:selected={categoryId}
            onchange={updateFilters}
          />
        </div>
      </fieldset>
    {/snippet}

    {#snippet headerRight()}
      <div class="gap-2 flex flex-wrap justify-end">
        <Button
          text={m['admin.suggestions.addCategory']()}
          icon="folder-add-line"
          variant="secondary"
          aria-controls="fr-modal-add-suggestion-category"
          data-fr-opened="false"
          onclick={openAddCategoryModal}
        />
        <Button
          text={m['admin.suggestions.add']()}
          icon="add-line"
          aria-controls="fr-modal-add-suggestion"
          data-fr-opened="false"
          onclick={openAddModal}
        />
      </div>
    {/snippet}

    {#snippet cell(row, col)}
      {#if col.id === 'text'}
        <span class="fr-text--sm whitespace-pre-wrap">{row.text}</span>
      {:else if col.id === 'status'}
        <Badge
          size="sm"
          text={statusLabel(row.status)}
          variant={row.status === 'archived' ? 'orange' : 'green'}
        />
      {:else if col.id === 'locale'}
        <span class="fr-text--sm uppercase">{row.locale}</span>
      {:else if col.id === 'actions'}
        <div class="flex justify-end">
          <Button
            iconOnly
            variant="tertiary-no-outline"
            size="sm"
            title={row.status === 'archived'
              ? m['admin.suggestions.restore']()
              : m['admin.suggestions.archive']()}
            aria-label={`${row.status === 'archived' ? m['admin.suggestions.restore']() : m['admin.suggestions.archive']()}: ${row.text}`}
            onclick={() => openStatusModal(row)}
          >
            <Icon
              icon={row.status === 'archived' ? 'i-ri-inbox-unarchive-line' : 'i-ri-archive-line'}
            />
          </Button>
        </div>
      {:else if col.id === 'category_title'}
        <span class="fr-text--sm">{row.category_title}</span>
      {:else}
        <span class="fr-text--sm">{row.text}</span>
      {/if}
    {/snippet}
  </Table>

  {#if data.suggestions.total === 0}
    <p class="fr-text--sm mt-4! text-[--text-mention-grey]">{m['admin.suggestions.empty']()}</p>
  {/if}

  <div class="mt-4 flex justify-center">
    <Pagination
      bind:page={currentPage}
      itemCount={data.suggestions.total}
      maxItemPerPage={data.suggestions.page_size}
    />
  </div>
</PageLayout>

<Modal id="fr-modal-add-suggestion-category" titleId="fr-modal-title-add-suggestion-category">
  <h2 id="fr-modal-title-add-suggestion-category" class="fr-modal__title">
    {m['admin.suggestions.addCategory']()}
  </h2>
  <form onsubmit={createCategory}>
    <Select
      id="suggestion-category-locale"
      label={m['admin.suggestions.locale']()}
      options={categoryLocaleOptions}
      bind:selected={categoryLocale}
      required
    />
    <div class="fr-input-group">
      <label class="fr-label" for="suggestion-category-title">
        {m['admin.suggestions.categoryTitle']()}
      </label>
      <input
        id="suggestion-category-title"
        class="fr-input"
        bind:value={categoryTitle}
        required
        maxlength="255"
      />
    </div>
    <div class="fr-input-group">
      <label class="fr-label" for="suggestion-category-description">
        {m['admin.suggestions.categoryDescription']()}
        <span class="fr-hint-text">{m['admin.suggestions.categoryDescriptionHint']()}</span>
      </label>
      <textarea
        id="suggestion-category-description"
        class="fr-input"
        bind:value={categoryDescription}
        required
        maxlength="1000"
      ></textarea>
    </div>
    <div class="gap-3 sm:grid-cols-[1fr_auto] sm:items-end grid">
      <Select
        id="suggestion-category-icon"
        label={m['admin.suggestions.categoryIcon']()}
        options={categoryIconOptions}
        bind:selected={categoryIcon}
        required
      />
      <div class="pb-4 text-center">
        <Icon icon={categoryIcon} aria-label={m['admin.suggestions.categoryIconPreview']()} />
      </div>
    </div>
    <div class="fr-input-group">
      <label class="fr-label" for="suggestion-category-tooltip">
        {m['admin.suggestions.categoryTooltip']()}
        <span class="fr-hint-text">{m['admin.suggestions.categoryTooltipHint']()}</span>
      </label>
      <textarea
        id="suggestion-category-tooltip"
        class="fr-input"
        bind:value={categoryTooltip}
        maxlength="4000"
        aria-describedby="suggestion-category-messages"
      ></textarea>
    </div>
    {#if categoryFormError}
      <div class="fr-messages-group" id="suggestion-category-messages" aria-live="polite">
        <p class="fr-message fr-message--error">{categoryFormError}</p>
      </div>
    {/if}
    <div class="fr-btns-group fr-btns-group--inline-md mt-4">
      <Button
        type="button"
        text={m['admin.suggestions.cancel']()}
        variant="secondary"
        onclick={() => closeModal('fr-modal-add-suggestion-category')}
      />
      <Button
        type="submit"
        text={m['admin.suggestions.addCategory']()}
        icon="folder-add-line"
        disabled={categoryFormLoading}
      />
    </div>
  </form>
</Modal>

<Modal id="fr-modal-add-suggestion" titleId="fr-modal-title-add-suggestion">
  <h2 id="fr-modal-title-add-suggestion" class="fr-modal__title">
    {m['admin.suggestions.add']()}
  </h2>
  <form onsubmit={createSuggestion}>
    <div class="fr-select-group">
      <label class="fr-label" for="suggestion-locale">{m['admin.suggestions.locale']()}</label>
      <select
        id="suggestion-locale"
        class="fr-select"
        bind:value={promptLocale}
        onchange={() => (promptCategoryId = '')}
      >
        {#each promptLocaleOptions as option (option.value)}
          <option value={option.value}>{option.label}</option>
        {/each}
      </select>
    </div>
    <Select
      id="suggestion-category"
      label={m['admin.suggestions.category']()}
      options={promptCategoryOptions}
      bind:selected={promptCategoryId}
      required
    />
    <div class={['fr-input-group', { 'fr-input-group--error': !!formError }]}>
      <label class="fr-label" for="suggestion-text">
        {m['admin.suggestions.prompt']()}
        <span class="fr-hint-text">{m['admin.suggestions.promptHint']()}</span>
      </label>
      <textarea
        id="suggestion-text"
        class="fr-input"
        bind:value={prompt}
        required
        maxlength="4000"
        aria-describedby="suggestion-text-messages"
      ></textarea>
      {#if formError}
        <div class="fr-messages-group" id="suggestion-text-messages" aria-live="polite">
          <p class="fr-message fr-message--error">{formError}</p>
        </div>
      {/if}
    </div>
    <div class="fr-btns-group fr-btns-group--inline-md mt-4">
      <Button
        type="button"
        text={m['admin.suggestions.cancel']()}
        variant="secondary"
        onclick={() => closeModal('fr-modal-add-suggestion')}
      />
      <Button
        type="submit"
        text={m['admin.suggestions.add']()}
        icon="add-line"
        disabled={formLoading}
      />
    </div>
  </form>
</Modal>

<Modal id="fr-modal-suggestion-status" titleId="fr-modal-title-suggestion-status">
  <h2 id="fr-modal-title-suggestion-status" class="fr-modal__title">
    {suggestionToToggle?.status === 'archived'
      ? m['admin.suggestions.restore']()
      : m['admin.suggestions.archive']()}
  </h2>
  <p>
    {suggestionToToggle?.status === 'archived'
      ? m['admin.suggestions.restoreConfirm']()
      : m['admin.suggestions.archiveConfirm']()}
  </p>
  <div class="fr-btns-group fr-btns-group--inline-md">
    <Button
      text={m['admin.suggestions.cancel']()}
      variant="secondary"
      onclick={() => closeModal('fr-modal-suggestion-status')}
    />
    <Button
      text={m['admin.suggestions.confirm']()}
      disabled={actionLoading}
      onclick={confirmStatusChange}
    />
  </div>
</Modal>
