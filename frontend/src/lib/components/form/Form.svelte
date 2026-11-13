<script lang="ts">
  import { browser } from '$app/environment'
  import { beforeNavigate } from '$app/navigation'
  import { Button } from '$components/dsfr'
  import AnyFormItem from '$components/form/AnyFormItem.svelte'
  import { m } from '$lib/i18n/messages'
  import { toEntries } from '$lib/utils/commons'
  import { getItemLabel, type AnyFormItemProps, type FormSection } from '$lib/utils/form'
  import type { Snippet } from 'svelte'
  import { onMount } from 'svelte'
  import type { SvelteHTMLElements } from 'svelte/elements'

  let {
    id,
    label,
    subLabel,
    description,
    items,
    sections,
    form,
    isBusy = false,
    isDirty = false,
    stickyFooter = false,
    errors = $bindable({}),
    novalidate = true,
    fieldSnippets,
    errorSnippet,
    btnSnippet,
    children,
    onSubmit,
    ...props
  }: Omit<SvelteHTMLElements['form'], 'method'> & {
    label?: string
    subLabel?: string
    description?: string
    items?: AnyFormItemProps[]
    // When set, only the items the sections list are shown, in their order
    sections?: FormSection[]
    form: Record<string, unknown>
    isBusy?: boolean
    isDirty?: boolean
    errors?: Record<string, string>
    stickyFooter?: boolean
    fieldSnippets?: Record<string, Snippet>
    errorSnippet?: Snippet
    btnSnippet?: Snippet<[isBusy: boolean]>
    onSubmit: () => void
  } = $props()

  const anyError = $derived(toEntries(errors))
  const errorLabel = (errId: string) =>
    (items && getItemLabel(items, errId)) || (errId === 'unexpected' ? undefined : errId)

  beforeNavigate((navigation) => {
    if (!isDirty) return
    // Cancelling a document-leaving navigation delegates to the browser's
    // native confirmation dialog. In-app navigation can use our own message.
    if (navigation.type === 'leave' || !window.confirm(m['form.unsavedChanges']()))
      navigation.cancel()
  })

  onMount(() => {
    if (!browser) return
    const warnBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!isDirty) return
      event.preventDefault()
    }
    window.addEventListener('beforeunload', warnBeforeUnload)
    return () => window.removeEventListener('beforeunload', warnBeforeUnload)
  })
</script>

<form
  {id}
  {...props}
  onsubmit={(event) => {
    event.preventDefault()
    onSubmit()
  }}
  {novalidate}
  aria-describedby="errors-{id}"
>
  <!-- Sections draw their own boxes, so they need no inset -->
  <div class={{ 'my-6': stickyFooter, 'px-4 md:px-6': stickyFooter && !sections }}>
    {#if label}
      <h2 id="{id}-title" class="text-3xl!">
        {label}
        {#if subLabel}
          <span class="text-grey text-base">{subLabel}</span>
        {/if}
      </h2>
    {/if}

    {#if description}
      <p class="text-sm! text-grey mb-6!">{description}</p>
    {/if}

    {#snippet field(itemId: string)}
      {@const item = items?.find((item) => item.id === itemId)}
      {#if fieldSnippets?.[itemId]}
        {@render fieldSnippets[itemId]()}
      {:else if item}
        <AnyFormItem {...item} bind:value={form[item.id]!} {errors} />
      {/if}
    {/snippet}

    <!-- Auto form fields -->
    {#if sections}
      {#each sections as section (section.id)}
        <section class="mb-6 p-4 md:p-6 cg-border" aria-labelledby="{id}-{section.id}-title">
          <h2 id="{id}-{section.id}-title" class="fr-h5 mb-1!">{section.title}</h2>
          {#if section.intro}
            <p class="fr-text--sm mb-5! text-[--text-mention-grey]">{section.intro}</p>
          {/if}
          {#each section.items as row, i (i)}
            {#if Array.isArray(row)}
              <div class="sm:grid-cols-2 sm:gap-x-6 grid">
                {#each row as itemId (itemId)}
                  {@render field(itemId)}
                {/each}
              </div>
            {:else}
              {@render field(row)}
            {/if}
          {/each}
        </section>
      {/each}
    {:else if items}
      {#each items as item (item.id)}
        {@render field(item.id)}
      {/each}
    {/if}

    {@render children?.()}

    <div class="fr-messages-group mb-4" id="errors-{id}" aria-live="polite">
      {#if errorSnippet}
        {@render errorSnippet()}
      {/if}
      {#if anyError.length}
        <ul class="fr-message fr-message--error block!">
          {m['form.containsErrors']()}
          {#each anyError as [errId, errMsg], i (i)}
            <li class="block!">
              {#if errorLabel(errId)}
                <a href="#{errId}">"{errorLabel(errId)}"</a>:
              {/if}
              {errMsg}
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  </div>

  <div
    class={[
      'py-4 gap-4 flex justify-end',
      {
        'bottom-0 bg-white sticky z-501 border-t-1 border-[--grey-925-125]': stickyFooter,
        'px-4 md:px-6': stickyFooter && !sections
      }
    ]}
  >
    {#if btnSnippet}
      {@render btnSnippet(isBusy)}
    {:else}
      <Button
        type="submit"
        text={isBusy ? m['form.busy']() : m['words.save']()}
        disabled={isBusy}
      />
    {/if}
  </div>
</form>
