<script lang="ts">
  import { browser } from '$app/environment'
  import { beforeNavigate } from '$app/navigation'
  import { Button } from '$components/dsfr'
  import AnyFormItem from '$components/form/AnyFormItem.svelte'
  import { m } from '$lib/i18n/messages'
  import { toEntries } from '$lib/utils/commons'
  import type { AnyFormItemProps } from '$lib/utils/form'
  import type { Snippet } from 'svelte'
  import { onMount } from 'svelte'
  import type { SvelteHTMLElements } from 'svelte/elements'

  let {
    id,
    label,
    subLabel,
    description,
    items,
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
    label: string
    subLabel?: string
    description?: string
    items?: AnyFormItemProps[]
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
  <div class={{ 'px-4 md:px-6 my-6': stickyFooter }}>
    <h2 id="{id}-title" class="text-3xl!">
      {label}
      {#if subLabel}
        <span class="text-grey text-base">{subLabel}</span>
      {/if}
    </h2>

    {#if description}
      <p class="text-sm! text-grey mb-6!">{description}</p>
    {/if}

    <!-- Auto form fields -->
    {#if items}
      {#each items as item (item.id)}
        {#if fieldSnippets?.[item.id]}
          {@render fieldSnippets[item.id]()}
        {:else}
          <AnyFormItem {...item} bind:value={form[item.id]!} {errors} />
        {/if}
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
              <a href="#{errId}">"{items?.find((item) => item.id === errId)?.label ?? errId}"</a>:
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
        'bottom-0 bg-white px-4 md:px-6 sticky z-501 border-t-1 border-[--grey-925-125]':
          stickyFooter
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
