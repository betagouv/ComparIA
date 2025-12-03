<script
  lang="ts"
  generics="
    Multiple extends boolean, 
    Kind extends 'checkbox' | 'radio', 
    V extends string, Value extends Kind extends 'checkbox' ? Multiple extends true ?  V[]: V : V, 
    Option extends { value: V, label: string }
  "
>
  import { type Snippet } from 'svelte'
  import type { ClassValue, HTMLInputAttributes } from 'svelte/elements'

  interface SelectorProps {
    id: string
    kind?: Kind
    choices: Option[]
    value: Value
    disabled?: boolean
    multiple?: Multiple
    max?: number
    containerClass?: ClassValue
    choiceClass?: ClassValue
    onChange?: (value: Value) => void
    option?: Snippet<
      [
        Option,
        { for: string; class: ClassValue },
        Snippet<[Option, HTMLInputAttributes] | [Option]>
      ]
    >
    extra?: Snippet<[{ class: ClassValue }]>
  }
  let {
    id,
    kind = 'checkbox' as Kind,
    value = $bindable(),
    choices,
    disabled = false,
    multiple = false as Multiple,
    max = Infinity,
    containerClass,
    choiceClass,
    onChange,
    option,
    extra
  }: SelectorProps = $props()

  const inputProps = $derived({
    name: id,
    disabled,
    onchange: (e: Event) => {
      if (!multiple) value = (e.target as HTMLInputElement).value as Value
      onChange?.(value)
    },
    class: 'sr-only'
  })
</script>

{#snippet input(choice: Option, props: HTMLInputAttributes = {})}
  {#if kind === 'checkbox'}
    {#if multiple}
      <input
        type="checkbox"
        bind:group={value}
        value={choice.value}
        id="{id}-{choice.value}"
        {...inputProps}
        {...props}
        disabled={disabled || (multiple && !value.includes(choice.value) && value.length >= max)}
      />
    {:else}
      <input
        type="checkbox"
        checked={(value as string) === choice.value}
        value={choice.value}
        id="{id}-{choice.value}"
        {...inputProps}
        {...props}
        disabled={disabled || (multiple && !value.includes(choice.value) && value.length >= max)}
      />
    {/if}
  {:else}
    <input
      type="radio"
      bind:group={value}
      value={choice.value}
      id="{id}-{choice.value}"
      {...inputProps}
      {...props}
    />
  {/if}
{/snippet}

<div {id} class={['cl-selector', containerClass]}>
  {#each choices as choice (choice.value)}
    {#if option}
      {@render option(
        choice,
        { for: `${id}-${choice.value}`, class: ['cg-border', choiceClass] },
        input
      )}
    {:else}
      <label for="{id}-{choice.value}" class={['cg-border', choiceClass]}>
        {@render input(choice)}
        {choice.label}
      </label>
    {/if}
  {/each}

  {#if extra}
    {@render extra({ class: ['cg-border', choiceClass] })}
  {/if}
</div>

<style>
  .cl-selector :global(label) {
    &:has(input) {
      margin: 1px;
    }

    &:has(input:focus) {
      outline: 2px solid var(--outline-color);
      outline-offset: 2px;
    }

    &:has(input:checked),
    &:has(input:active) {
      border: 2px solid var(--color-primary);
      color: var(--color-primary);
      margin: 0;
    }

    &:has(input:disabled) {
      filter: grayscale(100%);
    }
  }
</style>
