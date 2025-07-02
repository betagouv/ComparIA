<script context="module">
  let id = 0
</script>

<script lang="ts">
  import { createEventDispatcher } from 'svelte'

  export let display_value: string
  export let internal_value: string
  export let disabled = false
  export let selected: string | null = null

  const dispatch = createEventDispatcher<{ input: string }>()
  let is_selected = false

  // This function will handle the update of the selected state
  async function handle_input(selected: string | null, internal_value: string): Promise<void> {
    is_selected = selected === internal_value
    if (is_selected) {
      dispatch('input', internal_value)
    }
  }

  $: handle_input(selected, internal_value)

  // Handle label click or space/enter key press to toggle selection
  function handleSelection() {
    // If we don't want to reshuffle
    // if (disabled || selected === internal_value) return;
    if (disabled) return
    selected = internal_value
    dispatch('input', internal_value)
  }

  // Handle keydown event (Space or Enter)
  function handleKeyDown(event: KeyboardEvent) {
    if (event.key === ' ' || event.key === 'Enter') {
      event.preventDefault() // Prevent page scroll with spacebar
      handleSelection() // Trigger selection when space or enter is pressed
    }
  }
</script>

<!-- svelte-ignore a11y-no-noninteractive-element-to-interactive-role -->
<label
  class:disabled
  class:selected={is_selected}
  class="custom-card"
  data-testid="{internal_value}-radio-label"
  tabindex="0"
  role="radio"
  aria-checked={is_selected}
  on:click={handleSelection}
  on:keydown={handleKeyDown}
>
  {#if internal_value === 'model-a'}
    <svg class="inline" width="26" height="26"
      ><circle cx="13" cy="13" r="12" fill="#a96AFE" stroke="none" /></svg
    >
  {:else if internal_value === 'model-b'}
    <svg class="inline" width="26" height="26"
      ><circle cx="13" cy="13" r="12" fill="#ff9575" stroke="none" /></svg
    >
  {:else if internal_value === 'both-equal'}
    <svg width="26" height="26" viewBox="0 0 26 26" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="0.5" y="0.5" width="25" height="25" rx="12.5" fill="white" />
      <rect x="0.5" y="0.5" width="25" height="25" rx="12.5" stroke="#E5E5E5" />
      <path d="M20 9H6V11H20V9ZM20 15H6V17H20V15Z" fill="#1A1A1A" />
    </svg>
  {/if}
  <input
    {disabled}
    type="radio"
    name="radio-{++id}"
    value={internal_value}
    aria-checked={is_selected}
    bind:group={selected}
    aria-hidden="true"
  />
  <span>{display_value}</span>
</label>

<style>
  label {
    row-gap: 1rem;
    padding: 1rem;
    margin: 0.75rem;
    display: flex;
    flex-direction: column;
    text-align: center;
    align-items: center;
    justify-content: center;
    transition: var(--button-transition);
    cursor: pointer;
    box-shadow: var(--checkbox-label-shadow);
    outline: 1px solid #e5e5e5;
    border-radius: 0.5rem;
    background-color: white;
    color: var(--grey-200-850);
    font-weight: var(--checkbox-label-text-weight);
    line-height: var(--line-md);
    font-weight: 500;
    font-size: 1rem;
    /* font-size: 0.875em; */
    border-radius: 1.5rem;
  }

  @media (min-width: 48em) {
    label {
      padding-right: 1.5rem;
      column-gap: 0.5rem;
      flex-direction: row;
    }
  }
  label.selected,
  label:active {
    /* color: #606367; */
    /* border: 1px #DADCE0 solid; */

    background: var(--blue-france-975-75);
    color: var(--blue-france-main-525);
    /* border: 1px var(--blue-france-main-525) solid; */
    outline-offset: 0 !important;
    outline: 2px solid var(--blue-france-main-525) !important;
  }
  /* 
	label > * + * {
		margin-left: var(--size-2);
	} */

  input[type='radio'] {
    display: none; /* Hide the actual radio button */
  }

  input[disabled],
  .disabled {
    cursor: not-allowed;
  }
</style>
