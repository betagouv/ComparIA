<script lang="ts">
  import type { Mode, ModeInfos } from '$lib/chatService.svelte'
  import Icon from '$lib/components/Icon.svelte'

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

<div>
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
      <div class="icon">
        <Icon {icon} class="text-primary" />
      </div>
      <div class="description">
        {#if value != 'custom'}
          <strong>{label}</strong>&nbsp;: {description}
        {:else}
          <strong>{label}</strong>
          <Icon icon="arrow-right-s-line" size="sm" class="float-right" />
        {/if}
      </div>
    </label>
  {/each}
</div>

<style>
  label.selected,
  label:active,
  label:focus {
    outline: 2px solid #6a6af4 !important;
    /* border: 2px solid var(--blue-france-main-525); */
  }

  label {
    border-radius: 0.5em;
    outline: 1px solid #e5e5e5;
    display: grid;
    padding: 1em 0.5em;
    align-items: center;
    grid-template-columns: auto 1fr;
    margin: 0.75em 0;
  }

  label .icon {
    padding: 0 0.5em 0 0.5em;
  }

  input[type='radio'] {
    position: fixed;
    opacity: 0;
    pointer-events: none;
  }
  /* p {
		color: #666666 !important;
		font-size: 0.875em !important;
	} */
  .description {
    font-size: 0.875em;
    color: #3a3a3a;
  }
</style>
