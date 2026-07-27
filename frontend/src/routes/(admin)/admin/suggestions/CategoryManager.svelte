<script lang="ts">
  import { Button, Icon } from '$components/dsfr'
  import { api } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import type { SuggestionCategory } from './types'

  let {
    categories,
    onDeleted
  }: {
    categories: SuggestionCategory[]
    onDeleted: () => Promise<void> | void
  } = $props()

  let categoryToDelete = $state<SuggestionCategory | null>(null)
  let deleting = $state(false)
  let error = $state<string>()

  const sortedCategories = $derived(
    [...categories].sort(
      (left, right) =>
        left.locale.localeCompare(right.locale) ||
        left.display_order - right.display_order ||
        left.title.localeCompare(right.title)
    )
  )

  function selectForDeletion(category: SuggestionCategory) {
    if (category.suggestion_count > 0) return
    categoryToDelete = category
    error = undefined
  }

  async function deleteCategory() {
    if (!categoryToDelete) return

    deleting = true
    error = undefined
    try {
      await api.request(`/admin/suggestions/categories/${categoryToDelete.id}`, {
        method: 'DELETE'
      })
      categoryToDelete = null
      useToast(m['admin.suggestions.categoryDeleteSuccess'](), 4000)
      await onDeleted()
    } catch (requestError) {
      const message = (requestError as Error).message
      error = message.includes('409')
        ? m['admin.suggestions.categoryDeleteConflict']()
        : m['admin.suggestions.categoryDeleteError']()
    } finally {
      deleting = false
    }
  }
</script>

<p class="fr-text--sm">
  {m['admin.suggestions.categoryDeleteIntro']()}
</p>

{#if sortedCategories.length === 0}
  <p>{m['admin.suggestions.noCategories']()}</p>
{:else}
  <ul class="m-0! p-0! list-none!">
    {#each sortedCategories as category (category.id)}
      {@const deletionStatus =
        category.suggestion_count === 0
          ? m['admin.suggestions.categoryEmpty']()
          : category.suggestion_count === 1
            ? m['admin.suggestions.categorySuggestionCount']()
            : m['admin.suggestions.categorySuggestionsCount']({
                count: category.suggestion_count
              })}
      <li
        class="gap-4 py-3 md:flex-row md:items-center flex flex-col border-b border-b-[--border-default-grey]"
      >
        <p class="m-0! min-w-0 gap-2 font-bold flex flex-1 items-center">
          <Icon icon={category.icon} aria-hidden="true" />
          <span>{category.title}</span>
          <span class="fr-badge fr-badge--sm fr-badge--no-icon uppercase">
            {category.locale}
          </span>
        </p>
        <div class="relative">
          <Button
            variant="tertiary"
            size="sm"
            class="gap-2"
            aria-disabled={category.suggestion_count > 0}
            aria-describedby={category.suggestion_count > 0
              ? `category-${category.id}-deletion-status`
              : undefined}
            title={category.suggestion_count > 0 ? deletionStatus : undefined}
            onclick={() => selectForDeletion(category)}
          >
            <Icon icon="i-ri-delete-bin-line" aria-hidden="true" />
            <span>{m['admin.suggestions.delete']()}</span>
          </Button>
          {#if category.suggestion_count > 0}
            <span
              id={`category-${category.id}-deletion-status`}
              class="fr-tooltip fr-placement max-w-64 font-normal z-2000! normal-case"
              role="tooltip"
            >
              {deletionStatus}
            </span>
          {/if}
        </div>
      </li>
    {/each}
  </ul>
{/if}

{#if categoryToDelete}
  <div class="fr-alert fr-alert--warning mt-4" role="alert">
    <h3 class="fr-alert__title">
      {m['admin.suggestions.categoryDeleteConfirm']({ title: categoryToDelete.title })}
    </h3>
    <p>{m['admin.suggestions.categoryDeleteWarning']()}</p>
    <div class="fr-btns-group fr-btns-group--inline-md mb-0! mt-3!">
      <Button
        variant="secondary"
        text={m['admin.suggestions.cancel']()}
        disabled={deleting}
        onclick={() => (categoryToDelete = null)}
      />
      <Button
        text={m['admin.suggestions.deleteCategory']()}
        disabled={deleting}
        onclick={deleteCategory}
      />
    </div>
  </div>
{/if}

{#if error}
  <p class="fr-error-text mt-3" aria-live="polite">{error}</p>
{/if}
