<script lang="ts">
  import { Button } from '$components/dsfr'
  import { api, ValidationError } from '$lib/fastapi-client'
  import { toEntries } from '$lib/utils/commons'
  import type { AnyFormItemProps } from '$lib/utils/form'
  import type { SvelteHTMLElements } from 'svelte/elements'
  import AnyFormItem from './AnyFormItem.svelte'

  let {
    id,
    label,
    subLabel,
    items,
    form,
    errors = $bindable({}),
    url,
    method = 'post',
    ...props
  }: Omit<SvelteHTMLElements['form'], 'method'> & {
    label: string
    subLabel?: string
    items: AnyFormItemProps[]
    form: Record<string, any>
    errors?: Record<string, string>
    url: string
    method?: 'post' | 'put'
  } = $props()

  async function onSubmit() {
    errors = {}
    try {
      await api.request(url, { body: JSON.stringify(form), method })
    } catch (e) {
      if (e instanceof ValidationError) {
        e.errors.forEach((err) => {
          const [_body, ...rest] = err.loc
          errors[rest.join('-')] = err.msg
        })
      }
    }
  }

  const anyError = $derived(toEntries(errors))
</script>

<form
  {id}
  {...props}
  onsubmit={onSubmit}
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
    <AnyFormItem {...item} bind:value={form[item.id]!} {errors} />
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

  <Button type="submit" text="submit" />
</form>
