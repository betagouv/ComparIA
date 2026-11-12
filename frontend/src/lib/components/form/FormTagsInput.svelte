<script module lang="ts">
  export type FormTagsInputProps = {
    // Values offered while typing, without limiting the field to them.
    suggestions?: string[]
    placeholder?: string
  } & BaseFormFieldProps<'tags'>
</script>

<script lang="ts">
  import { m } from '$lib/i18n/messages'
  import type { BaseFormFieldProps } from '$lib/utils/form'
  import { FormField } from '.'
  import ChipList from './ChipList.svelte'

  let {
    value = $bindable(),
    disabled,
    suggestions = [],
    placeholder,
    component: _component,
    ...props
  }: FormTagsInputProps & { value?: string[] | null } = $props()

  let draft = $state('')
  let input = $state<HTMLInputElement>()
  const values = $derived(value ?? [])
  const offered = $derived(suggestions.filter((suggestion) => !values.includes(suggestion)))

  // A comma or Enter ends a value, so several can be pasted at once.
  function commit(text = draft) {
    const added = text
      .split(',')
      .map((part) => part.trim())
      .filter((part) => part && !values.includes(part))
    if (added.length) value = [...values, ...new Set(added)]
    draft = ''
  }

  function remove(tag: string) {
    value = values.filter((other) => other !== tag)
  }

  function onkeydown(event: KeyboardEvent) {
    if (event.key === 'Enter' || event.key === ',') {
      // Enter would otherwise submit the whole form.
      event.preventDefault()
      commit()
    } else if (event.key === 'Backspace' && !draft && values.length) {
      remove(values[values.length - 1])
    }
  }
</script>

<FormField {...props} component="input">
  {#snippet formItem(fieldProps)}
    <div class="mt-2">
      <ChipList
        label={props.label}
        items={values.map((tag) => ({ value: tag, label: tag }))}
        {disabled}
        onremove={remove}
        onempty={() => input?.focus()}
        class="mb-2!"
      />
      <input
        bind:this={input}
        {...fieldProps}
        type="text"
        class="fr-input"
        autocomplete="off"
        list={offered.length ? `${props.id}-suggestions` : undefined}
        placeholder={placeholder ?? m['form.tags.placeholder']()}
        {disabled}
        bind:value={draft}
        {onkeydown}
        onchange={() => {
          // Picking a suggestion from the list fires change without a key.
          if (offered.includes(draft.trim())) commit()
        }}
        onblur={() => commit()}
      />
      {#if offered.length}
        <datalist id="{props.id}-suggestions">
          {#each offered as suggestion (suggestion)}
            <option value={suggestion}></option>
          {/each}
        </datalist>
      {/if}
    </div>
  {/snippet}
</FormField>

<style lang="postcss">
  .fr-input {
    --border-plain-grey: var(--blue-france-main-525);
    --background-contrast-grey: var(--blue-ecume-975-75);
  }
</style>
