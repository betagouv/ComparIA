<script lang="ts">
  let {
    onvote,
    disabled = false
  }: {
    onvote: (chosen: 'a' | 'b' | 'tie') => void
    disabled?: boolean
  } = $props()

  let selected = $state<'a' | 'b' | 'tie' | null>(null)

  const choices = [
    { value: 'a' as const, label: 'Tool A' },
    { value: 'tie' as const, label: 'Tie' },
    { value: 'b' as const, label: 'Tool B' }
  ]

  function handleSelect(value: 'a' | 'b' | 'tie') {
    selected = value
    onvote(value)
  }
</script>

<div id="vote-area" class="fr-container py-7 md:py-20">
  <div class="text-center">
    <h4 class="fr-h6 mb-2!">Which result is better?</h4>
    <p class="fr-text--sm text-grey">Select the tool that best achieved the goal</p>
  </div>

  <fieldset id="tool-vote-cards" aria-labelledby="tool-vote-legend">
    <legend class="sr-only" id="tool-vote-legend">Which result is better?</legend>

    <div class="gap-5 md:flex md:justify-center grid auto-rows-max grid-cols-3">
      {#each choices as { value, label } (value)}
        <div class="h-full">
          <input
            type="radio"
            id="tool-radio-{value}"
            name="tool-vote-radio-group"
            {value}
            disabled={disabled}
            checked={selected === value}
            onchange={() => handleSelect(value)}
            class="sr-only"
          />
          <label
            class="cg-border md:rounded-[56px]! px-3 py-4 font-medium md:flex-row md:justify-center flex h-full flex-col items-center justify-center text-center cursor-pointer"
            for="tool-radio-{value}"
          >
            {#if value === 'tie'}
              <svg
                width="26"
                height="26"
                viewBox="0 0 26 26"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                aria-hidden="true"
              >
                <rect x="0.5" y="0.5" width="25" height="25" rx="12.5" fill="white" />
                <rect x="0.5" y="0.5" width="25" height="25" rx="12.5" stroke="#E5E5E5" />
                <path d="M20 9H6V11H20V9ZM20 15H6V17H20V15Z" fill="#1A1A1A" />
              </svg>
            {:else}
              <div class="c-bot-disk-{value}"></div>
            {/if}
            <span class="mt-3 md:ms-3 md:mt-0">{label}</span>
          </label>
        </div>
      {/each}
    </div>
  </fieldset>
</div>

<style>
  input:focus + label {
    outline: 2px solid var(--outline-color);
    outline-offset: 2px;
  }
  input:checked + label {
    border: 2px solid var(--blue-france-main-525);
    background: var(--blue-france-975-75);
    color: var(--blue-france-main-525);
  }
</style>
