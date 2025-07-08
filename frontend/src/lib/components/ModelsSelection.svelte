<script lang="ts">
  import type { Model } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'

  export let custom_models_selection: string[] = [] // Default to an empty list
  export let models: Model[] = []

  export let disabled = false

  export let toggle_model_selection: (id: string) => void

  function handleKeyDown(id: string, event: KeyboardEvent) {
    if (event.key === ' ' || event.key === 'Enter') {
      event.preventDefault()
      toggle_model_selection(id)
    }
  }
</script>

<div class="models-grid">
  {#each models as { id, simple_name, icon_path, organisation, params, total_params, friendly_size, distribution, release_date, fully_open_source }, index}
    <!-- svelte-ignore a11y-no-noninteractive-element-to-interactive-role -->
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <label
      class:selected={custom_models_selection.includes(id)}
      class:disabled={disabled ||
        (!custom_models_selection.includes(id) && custom_models_selection.length == 2)}
      data-testid={`radio-label-${id}`}
      tabindex="0"
      role="radio"
      aria-checked={custom_models_selection.includes(id) ? 'true' : 'false'}
      on:keydown={(e) => handleKeyDown(id, e)}
    >
      <input
        type="radio"
        name="radio-options"
        value={id}
        data-index={index}
        aria-checked={custom_models_selection.includes(id)}
        disabled={disabled ||
          (!custom_models_selection.includes(id) && custom_models_selection.length == 2)}
        on:click={(e) => {
          toggle_model_selection(id)
          e.stopPropagation()
        }}
      />
      <div>
        <span class="icon">
          <img src="../assets/orgs/{icon_path}" alt={organisation} width="20" class="inline" />
        </span>&nbsp;<span class="organisation">{organisation}/</span><strong>{simple_name}</strong>
      </div>
      <div>
        <span
          class:fr-badge--yellow-tournesol={distribution == 'open-weights' && !fully_open_source}
          class:fr-badge--orange-terre-battue={distribution == 'api-only'}
          class:fr-badge--green-emeraude={distribution == 'open-weights' && fully_open_source}
          class="fr-badge fr-badge--sm fr-badge--no-icon fr-mr-1v fr-mb-1v"
        >
          {distribution == 'api-only'
            ? m['models.licenses.proprietary']
            : fully_open_source
              ? m['models.licenses.openSource']
              : m['models.licenses.semiOpen']}
        </span>
        {#if release_date}
          <span class="fr-badge fr-badge--sm fr-badge--no-icon fr-mr-1v">
            {m['models.release']({ date: release_date })}
          </span>
        {/if}
        <span class="fr-badge fr-badge--sm fr-badge--info fr-badge--no-icon fr-mr-1v fr-mb-1v">
          {#if distribution === 'api-only'}
            {m['models.size']({ size: friendly_size })}
          {:else}
            {m['models.parameters']({ number: typeof params === 'number' ? params : total_params })}
          {/if}
        </span>
      </div>
    </label>
  {/each}
</div>

<style>
  .models-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.5em;
  }

  @media (min-width: 48em) {
    .models-grid {
      grid-template-columns: 1fr 1fr 1fr;
      gap: 1em;
    }
  }
  label.selected,
  label.selected:active,
  label.selected:focus {
    outline: 2px solid #6a6af4 !important;
  }

  /* label:not([disabled]):active { */
  label:active,
  label:focus {
    outline: 2px solid #ccc !important;
  }

  label.disabled,
  label.disabled:active,
  label.disabled:focus {
    filter: grayscale(100%);
    outline: 1px solid #ccc !important;
  }
  label {
    border-radius: 0.5em;
    outline: 1px solid #e5e5e5;
    display: grid;
    align-items: center;
    /* grid-template-columns: auto 1fr; */
    padding: 0.25em 0;
  }

  label .icon {
    padding: 0 0.5em 0 0.5em;
  }

  input[type='radio'],
  input[type='radio']:disabled {
    position: fixed;
    opacity: 0 !important;
    pointer-events: none;
  }
  /* p {
		color: #666666 !important;
		font-size: 0.875em !important;
	} */
  strong {
    font-size: 0.875em;
    color: #3a3a3a;
  }

  .fr-badge {
    display: none !important;
  }
  .organisation {
    color: rgb(36, 36, 36);
    display: none;
    font-size: 0.875em;
  }

  @media (min-width: 48em) {
    .fr-badge {
      display: inline !important;
    }
    .organisation {
      display: inline;
    }
    label {
      padding: 1em;
    }
  }
</style>
