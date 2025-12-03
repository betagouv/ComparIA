<script lang="ts">
  import { Icon } from '$components/dsfr'
  import type { HTMLButtonAttributes } from 'svelte/elements'

  // TODO: rework

  type IconButtonProps = Omit<HTMLButtonAttributes, 'size'> & {
    icon: string
    label?: string
    show_label?: boolean
    pending?: boolean
    size?: 'small' | 'large' | 'medium'
    padded?: boolean
    highlight?: boolean
    border?: boolean
    disabled?: boolean
    hasPopup?: boolean
    transparent?: boolean
  }
  let {
    icon,
    label = '',
    show_label = false,
    pending = false,
    size = 'medium',
    padded = true,
    highlight = false,
    border = false,
    disabled = false,
    hasPopup = false,
    transparent = false,
    ...props
  }: IconButtonProps = $props()
</script>

<button
  {disabled}
  aria-label={label}
  aria-haspopup={hasPopup}
  title={label}
  class:pending
  class:padded
  class:border
  class:highlight
  class:transparent
  {...props}
>
  {#if show_label}<span>{label}</span>{/if}
  <div
    class:small={size === 'small'}
    class:large={size === 'large'}
    class:medium={size === 'medium'}
  >
    <Icon {icon} size="sm" class="text-primary" />
  </div>
</button>

<style>
  button {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 1px;
    z-index: var(--layer-2);
    border-radius: 50%;
    color: var(--block-label-text-color);
    padding: 10px;
  }

  button.border {
    border: 1px solid var(--grey-925-125) !important;
  }
  button.border.highlight {
    border: 1px solid var(--blue-france-main-525) !important;
    background-color: var(--blue-france-975-75) !important;
  }

  button[disabled] {
    opacity: 0.5;
    box-shadow: none;
    background-color: var(--grey-950-100) !important;
  }
  button.border.highlight[disabled] {
    border: 1px solid #606367 !important;
  }
  button[disabled]:hover {
    cursor: not-allowed;
  }

  .padded {
    background: var(--bg-color);
  }

  button:hover,
  button.highlight,
  button:hover > *,
  button.highlight > * {
    cursor: pointer;
    color: var(--blue-france-main-525);
  }

  .padded:hover {
    color: var(--block-label-text-color);
  }

  span {
    padding: 0px 1px;
    font-size: 10px;
  }

  div {
    display: flex;
    align-items: center;
    justify-content: center;
    transition: filter 0.2s ease-in-out;
  }

  .small {
    width: 14px;
    height: 14px;
  }

  .medium {
    width: 20px;
    height: 20px;
  }

  .large {
    width: 22px;
    height: 22px;
  }

  .pending {
    animation: flash 0.5s infinite;
  }

  @keyframes flash {
    0% {
      opacity: 0.5;
    }
    50% {
      opacity: 1;
    }
    100% {
      opacity: 0.5;
    }
  }

  .transparent {
    background: transparent;
    border: none;
    box-shadow: none;
  }
</style>
