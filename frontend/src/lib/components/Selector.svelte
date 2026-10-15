<script
  lang="ts"
  generics="
    Multiple extends boolean, 
    Kind extends 'checkbox' | 'radio', 
    V extends string, Value extends Kind extends 'checkbox' ? Multiple extends true ?  V[]: V : V, 
    Option extends { value: V, label: string, disabledReason?: string }
  "
>
  import { tick, type Snippet } from 'svelte'
  import type { ClassValue, HTMLInputAttributes } from 'svelte/elements'

  /**
   * A choice with a `disabledReason` cannot be picked, but stays in the tab
   * order with `aria-disabled`, described by its reason. A native `disabled`
   * input would drop out of it, and screen readers in focus mode skip it, so
   * the reason would be lost. Picking it speaks the reason instead, and sets
   * `tried`, for the card to show the reason too: on a phone nothing else
   * answers the tap.
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
    /** The choice last tried while it could not be picked, until another is. */
    tried?: V
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
    label,
    value = $bindable(),
    choices,
    disabled = false,
    multiple = false as Multiple,
    max = Infinity,
    containerClass,
    choiceClass,
    onChange,
    tried = $bindable(),
    option,
    extra
  }: SelectorProps = $props()

  const inputProps = $derived({
    name: id,
    disabled,
    onchange: (e: Event) => {
      if (!multiple) value = (e.target as HTMLInputElement).value as Value
      tried = undefined
      onChange?.(value)
    },
    class: 'sr-only'
  })

  // What the live region says when someone tries a choice they cannot pick.
  let said = $state('')

  function reasonProps(choice: Option): HTMLInputAttributes {
    if (!choice.disabledReason) return {}
    return {
      'aria-disabled': 'true',
      'aria-describedby': `${id}-${choice.value}-reason`,
      onclick: async (e: MouseEvent) => {
        e.preventDefault()
        tried = choice.value
        // Emptied first, so the same reason is spoken again on a second try.
        said = ''
        await tick()
        said = choice.disabledReason!
      }
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
        { for: `${id}-${choice.value}`, class: ['cg-border', choiceClass] },
        input
      )}
    {:else}
      <label for="{id}-{choice.value}" class={['cg-border', choiceClass]}>
        {@render input(choice)}
        {choice.label}
        {#if tried === choice.value}
          <!-- Seen in the card; read out through the live region and the description. -->
          <span class="cl-selector__reason fr-text--sm mb-0! mt-2 block" aria-hidden="true">
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

{#each choices as choice (choice.value)}
  {#if choice.disabledReason}
    <span id="{id}-{choice.value}-reason" hidden>{choice.disabledReason}</span>
  {/if}
{/each}
<!-- Present from first render: a live region only speaks what lands in it after. -->
<p role="status" class="sr-only">{said}</p>

<style>
  .cl-selector :global(.cl-selector__reason) {
    color: var(--text-mention-grey);
  }

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
      border: 2px solid var(--blue-france-main-525);
      color: var(--blue-france-main-525);
      margin: 0;
    }

    &:has(input:disabled) {
      filter: grayscale(100%);
    }

    &:has(input[aria-disabled='true']) {
      cursor: not-allowed;
    }
  }
</style>
