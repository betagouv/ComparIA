<script lang="ts">
  import { Icon } from '$components/dsfr'
  import type { Mode, ModeInfos } from '$lib/chatService.svelte'

  // FIXME a11y + css
  // TODO: might need to refacto w/ mapfilter func for only choice + custom_models_selection + models

  interface DropDownProps {
    choices: ModeInfos[]
    mode: Mode
    disabled?: boolean
    onOptionSelected: (mode: Mode) => void
  }

  let { choices, mode = $bindable(), disabled = false, onOptionSelected }: DropDownProps = $props()

  function onKeydown(event: KeyboardEvent, value: Mode) {
    if (event.key === ' ' || event.key === 'Enter') {
      event.preventDefault()
      onChange(value)
    }
  }

  function onChange(value: Mode) {
    mode = value
    onOptionSelected(mode)
  }
</script>

<div class="flex flex-col gap-3 md:gap-4">
  {#each choices as { value, label, icon, description }, index}
    <!-- svelte-ignore a11y-no-noninteractive-element-to-interactive-role -->
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <label
      class:selected={value === mode}
      class:disabled
      data-testid={`radio-label-${mode}`}
      tabindex="0"
      role="radio"
      aria-checked={value === mode ? 'true' : 'false'}
      class="text-dark-grey flex items-center p-4"
      onclick={() => onChange(value)}
      onkeydown={(e) => onKeydown(e, value)}
      aria-controls={value != 'custom' ? 'modal-mode-selection' : ''}
    >
      <input
        type="radio"
        name="radio-options"
        value={mode}
        data-index={index}
        aria-checked={value === mode}
        {disabled}
      />
      <Icon {icon} class="text-primary me-3" />
      {#if value != 'custom'}
        <div><strong>{label}</strong>&nbsp;: {description}</div>
      {:else}
        <strong>{label}</strong>
        <Icon icon="arrow-right-s-line" size="sm" class="ms-auto" />
      {/if}
    </label>
  {/each}
</div>

<style>
  label.selected,
  label:active,
  label:focus {
    outline: 2px solid var(--blue-france-main-525) !important;
  }

  label {
    border-radius: 0.5em;
    outline: 1px solid var(--grey-925-125);
    font-size: 0.875em;
  }

  input[type='radio'] {
    position: fixed;
    opacity: 0;
    pointer-events: none;
  }
</style>
