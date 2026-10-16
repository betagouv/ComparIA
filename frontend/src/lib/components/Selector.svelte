<script
  lang="ts"
  generics="
    Multiple extends boolean,
    Kind extends 'checkbox' | 'radio',
    V extends string, Value extends Kind extends 'checkbox' ? Multiple extends true ?  V[]: V : V,
    Option extends { value: V, label: string, disabledReason?: string }
  "
>
  import type { Snippet } from 'svelte'
  import type { ClassValue, HTMLInputAttributes } from 'svelte/elements'

  /**
   * A choice with a `disabledReason` cannot be picked: it stays in the tab
   * order with `aria-disabled`, greyed out, described by its reason. A native
   * `disabled` input would drop out of it, and screen readers in focus mode
   * skip it, so the reason would be lost. A custom `option` shows the reason
   * in the card, under the id it is given as `reasonId`.
   */
  interface SelectorProps {
    id: string
    kind?: Kind
    /** Names the whole set of choices, which screen readers otherwise announce one by one. */
    label?: string
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
        { for: string; class: ClassValue; reasonId: string },
        Snippet<[Option, HTMLInputAttributes] | [Option]>
      ]
    >
    extra?: Snippet<[{ class: ClassValue }]>
  }
  let {
    id,
    kind = 'checkbox' as Kind,
    label,
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

  const reasonId = (choice: Option) => `${id}-${choice.value}-reason`

  function reasonProps(choice: Option): HTMLInputAttributes {
    if (!choice.disabledReason) return {}
    return {
      'aria-disabled': 'true',
      'aria-describedby': reasonId(choice),
      onclick: (e: MouseEvent) => e.preventDefault()
    }
  }
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
        {...reasonProps(choice)}
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
        {...reasonProps(choice)}
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
      {...reasonProps(choice)}
    />
  {/if}
{/snippet}

<div
  {id}
  role={kind === 'radio' ? 'radiogroup' : 'group'}
  aria-label={label}
  class={['cl-selector', containerClass]}
>
  {#each choices as choice (choice.value)}
    {#if option}
      {@render option(
        choice,
        {
          for: `${id}-${choice.value}`,
          class: ['cg-border', choiceClass],
          reasonId: reasonId(choice)
        },
        input
      )}
    {:else}
      <label for="{id}-{choice.value}" class={['cg-border', choiceClass]}>
        {@render input(choice)}
        {choice.label}
        {#if choice.disabledReason}
          <!-- The input's description, kept out of its name. -->
          <span
            id={reasonId(choice)}
            class="cl-selector__reason fr-text--xs mb-0! mt-1 block"
            aria-hidden="true"
          >
            {choice.disabledReason}
          </span>
        {/if}
      </label>
    {/if}
  {/each}

  {#if extra}
    {@render extra({ class: ['cg-border', choiceClass] })}
  {/if}
</div>

<style>
  /* The bordered choice: the label itself, or the card around it. */
  .cl-selector :global(.cg-border) {
    &:has(input) {
      margin: 1px;
    }

    &:has(input:focus) {
      outline: 2px solid var(--outline-color);
      outline-offset: 2px;
    }

    /* A choice that cannot be picked never looks picked. */
    &:has(input:checked:not([aria-disabled='true'])),
    &:has(input:active:not([aria-disabled='true'])) {
      border: 2px solid var(--blue-france-main-525);
      color: var(--blue-france-main-525);
      margin: 0;
    }

    &:has(input:disabled) {
      filter: grayscale(100%);
    }

    /* Greyed out as DSFR does a disabled card, its text still readable. */
    &:has(input[aria-disabled='true']) {
      background-color: var(--background-alt-grey);
      color: var(--text-mention-grey);
      cursor: not-allowed;

      & :global(label) {
        cursor: not-allowed;
      }
    }
  }

  .cl-selector :global(.cl-selector__reason) {
    color: var(--text-mention-grey);
  }
</style>
