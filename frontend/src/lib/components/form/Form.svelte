<script lang="ts">
  import { beforeNavigate } from '$app/navigation'
  import { browser } from '$app/environment'
  import { Button } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { toEntries } from '$lib/utils/commons'
  import type { AnyFormItemProps } from '$lib/utils/form'
  import type { Snippet } from 'svelte'
  import type { SvelteHTMLElements } from 'svelte/elements'
  import { onMount } from 'svelte'
  import AnyFormItem from './AnyFormItem.svelte'

  let {
    id,
    label,
    subLabel,
    items,
    form,
    isDirty = false,
    errors = $bindable({}),
    fieldSnippets,
    children,
    onSubmit,
    ...props
  }: Omit<SvelteHTMLElements['form'], 'method'> & {
    label: string
    subLabel?: string
    items: AnyFormItemProps[]
    form: Record<string, any>
    isDirty?: boolean
    errors?: Record<string, string>
    fieldSnippets?: Record<string, Snippet>
    onSubmit: () => void
  } = $props()

  const anyError = $derived(toEntries(errors))

  const unsavedMessage = 'You have unsaved changes. Are you sure you want to leave?'

  beforeNavigate((navigation) => {
    if (!isDirty) return
    // Cancelling a document-leaving navigation delegates to the browser's
    // native confirmation dialog. In-app navigation can use our own message.
    if (navigation.type === 'leave' || !window.confirm(unsavedMessage)) navigation.cancel()
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
  aria-describedby="errors-{id}"
  class={['mt-6! p-6 cg-border max-w-[700px]', props.class]}
>
  <h2 class="text-2xl! b-b-1 b-grey">
    {label}
    {#if subLabel}
      <span class="text-grey text-base">{subLabel}</span>
    {/if}
  </h2>

  {#each items as item (item.id)}
    {#if fieldSnippets?.[item.id]}
      {@render fieldSnippets[item.id]()}
    {:else}
      <AnyFormItem {...item} bind:value={form[item.id]!} {errors} />
    {/if}
  {/each}

  {#if anyError.length}
    <div class="fr-messages-group" id="errors-{id}" aria-live="polite">
      <ul class="fr-message fr-message--error block!">
        The form contains errors:
        {#each anyError as [errId, errMsg], i (i)}
          <li class="block!"><a href="#{errId}">"{errId}"</a>: {errMsg}</li>
        {/each}
      </ul>
    </div>
  {/if}

  <Button type="submit" text={m['words.save']()} />
</form>
