<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import { Badge } from '$components/dsfr'
  import type { BotModel } from '$lib/models'

  // FIXME ally, rework as Selector checkbox
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

<div class="grid grid-cols-2 gap-3 md:grid-cols-3">
  {#each models as { id, simple_name, icon_path, organisation, badges }, index (id)}
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
      class="p-2 md:px-4 md:py-3"
      onkeydown={(e) => handleKeyDown(id, e)}
    >
      <input
        type="radio"
        name="radio-options"
        value={id}
        data-index={index}
        aria-checked={selection.includes(id)}
        disabled={disabled || (!selection.includes(id) && selection.length == 2)}
        onclick={(e) => {
          toggleModelSelection(id)
          e.stopPropagation()
        }}
      />
      <div class="flex text-dark-grey">
        <AILogo iconPath={icon_path} alt={organisation} class="me-2" />
        <span class="organisation hidden md:inline">{organisation}/</span><strong
          >{simple_name}</strong
        >
      </div>
      <ul class="fr-badges-group mt-3! hidden! md:flex!">
        {#each modelBadges as badge, i (i)}
          <li><Badge id="card-badge-{i}" size="xs" {...badge} noTooltip /></li>
        {/each}
      </ul>
    </label>
  {/each}
</div>

<style>
  label.selected,
  label.selected:active,
  label.selected:focus {
    outline: 2px solid var(--blue-france-main-525) !important;
  }

  /* label:not([disabled]):active { */
  label:active,
  label:focus {
    outline: 2px solid var(--grey-950-125-active) !important;
  }

  label.disabled,
  label.disabled:active,
  label.disabled:focus {
    filter: grayscale(100%);
    outline: 1px solid var(--grey-950-125-active) !important;
  }
  label {
    border-radius: 0.5em;
    outline: 1px solid var(--grey-925-125);
  }

  input[type='radio'],
  input[type='radio']:disabled {
    position: fixed;
    opacity: 0 !important;
    pointer-events: none;
  }

  strong,
  .organisation {
    font-size: 0.875em;
  }
</style>
