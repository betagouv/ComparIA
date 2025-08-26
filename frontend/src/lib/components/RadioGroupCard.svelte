<script
  lang="ts"
  generics="Value extends string, Option extends { value: Value, label: string, class?: ClassValue }"
>
  import type { Snippet } from 'svelte'
  import type { ClassValue, SvelteHTMLElements } from 'svelte/elements'

  type RadioGroupCardProps = {
    id: string
    options: Option[]
    value?: Value
    disabled?: boolean
    onChange?: (value: Value) => void
    item?: Snippet<[Option]>
  } & SvelteHTMLElements['div']
  let {
    id,
    value = $bindable(),
    options,
    disabled = false,
    onChange,
    item,
    ...props
  }: RadioGroupCardProps = $props()
</script>

<div {...props} {id} class={['grid gap-3 md:grid-cols-2 md:gap-6 lg:grid-cols-4', props.class]}>
  {#each options as option}
    <input
      id="{id}-{option.value}"
      name={id}
      bind:group={value}
      value={option.value}
      checked={value === option.value}
      type="radio"
      {disabled}
      class="sr-only"
      onchange={() => onChange?.(option.value)}
    />

    <label
      for="{id}-{option.value}"
      class={[
        'cg-border rounded-sm! text-dark-grey! px-4! py-3! md:py-5! flex items-center bg-white md:flex-col md:items-start',
        option.class
      ]}
    >
      {#if item}
        {@render item(option)}
      {:else}
        {option.label}
      {/if}
    </label>
  {/each}
</div>

<style>
  input + label {
    border: 1px var(--grey-925-125) solid;
  }

  input:focus + label {
    border: 2px solid var(--blue-france-main-525);
    outline: 2px solid var(--outline-color);
    outline-offset: 2px;
  }

  input:checked + label,
  input:active + label,
  input:focus + label {
    border: 2px solid var(--blue-france-main-525);
    color: var(--blue-france-main-525);
  }

  input:disabled + label {
    filter: grayscale(100%);
  }
</style>
