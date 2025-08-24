<script lang="ts">
  import { Badge } from '$lib/components/dsfr'
  import type { BotModel } from '$lib/models'

  // FIXME rework as Selector
  let {
    selection = $bindable([]),
    models,
    disabled = false,
    toggleModelSelection
  }: {
    selection: string[]
    models: BotModel[]
    disabled?: boolean
    toggleModelSelection: (id: string) => void
  } = $props()

  function handleKeyDown(id: string, event: KeyboardEvent) {
    if (event.key === ' ' || event.key === 'Enter') {
      event.preventDefault()
      toggleModelSelection(id)
    }
  }
</script>

<div class="models-grid">
  {#each models as { id, simple_name, icon_path, organisation, badges }, index}
    {@const modelBadges = (['license', 'releaseDate', 'size'] as const)
      .map((k) => badges[k])
      .filter((b) => !!b)}

    <label
      class:selected={selection.includes(id)}
      class:disabled={disabled || (!selection.includes(id) && selection.length == 2)}
      data-testid={`radio-label-${id}`}
      tabindex="0"
      role="radio"
      aria-checked={selection.includes(id) ? 'true' : 'false'}
      on:keydown={(e) => handleKeyDown(id, e)}
    >
      <input
        type="radio"
        name="radio-options"
        value={id}
        data-index={index}
        aria-checked={selection.includes(id)}
        disabled={disabled || (!selection.includes(id) && selection.length == 2)}
        on:click={(e) => {
          toggleModelSelection(id)
          e.stopPropagation()
        }}
      />
      <div>
        <span class="icon">
          <img src="/orgs/ai/{icon_path}" alt={organisation} width="20" class="inline" />
        </span><span class="organisation">{organisation}/</span><strong>{simple_name}</strong>
      </div>
      <ul class="fr-badges-group hidden! md:flex! mt-3!">
        {#each modelBadges as badge, i}
          <li><Badge id="card-badge-{i}" size="xs" {...badge} noTooltip /></li>
        {/each}
      </ul>
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

  .organisation {
    color: rgb(36, 36, 36);
    display: none;
    font-size: 0.875em;
  }

  @media (min-width: 48em) {
    .organisation {
      display: inline;
    }
    label {
      padding: 1em;
    }
  }
</style>
