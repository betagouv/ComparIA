<script lang="ts">
  import type { BotChoice } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'

  export interface VoteAreaProps {
    value?: BotChoice
    disabled?: boolean
  }

  let { value: selected = $bindable(), disabled = false }: VoteAreaProps = $props()

  const choices = [
    { value: 'a', label: m['models.names.a']() },
    { value: 'both_equal', label: m['vote.bothEqual']() },
    { value: 'b', label: m['models.names.b']() }
  ] as const
</script>

<fieldset id="vote-cards" aria-labelledby="vote-cards-legend">
  <legend class="sr-only" id="vote-cards-legend">{m['vote.title']()}</legend>

  <div class="gap-5 md:flex md:justify-center grid auto-rows-max grid-cols-3">
    {#each choices as { value, label } (value)}
      <div class="h-full">
        <input
          type="radio"
          id="radio-{value}"
          name="vote-radio-group"
          {value}
          {disabled}
          bind:group={selected}
          class="sr-only"
        />
        <label
          class="cg-border md:rounded-[56px]! px-3 py-4 font-medium md:flex-row md:justify-center flex h-full flex-col items-center justify-center text-center"
          for="radio-{value}"
        >
          {#if value === 'both_equal'}
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
