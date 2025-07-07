<script lang="ts">
  import { type Component } from 'svelte'

  let like_panel: HTMLDivElement
  export let show: boolean
  export let Icon: Component
  export let text: string
  export let commented: boolean = false
  export let disabled: boolean = false
  export let model: string = ''
  export let value: string[] = []
  export let choices: [string, string][]
  export let modalId: string
  export let onSelection: (selection: string[]) => void

  function toggle_choice(choice: string): void {
    if (value.includes(choice)) {
      value = value.filter((v) => v !== choice)
    } else {
      value = [...value, choice]
    }
    onSelection(value)
  }

  let hasBeenShown: boolean = false
  function scrollIntoViewWithOffset(element: HTMLElement, offset: number) {
    // For offset 0 just consider a footer of 100px (really is 114px)
    offset = Math.max(100, offset || 0)
    const rect = element.getBoundingClientRect()
    const viewportHeight = window.visualViewport?.height || window.innerHeight

    const isVisible = rect.bottom <= viewportHeight - offset

    if (!isVisible) {
      // this not enough because margins so let's just add some extra
      // const scrollTop = window.scrollY + rect.height;
      const scrollTop = window.scrollY + rect.height + offset
      window.scrollTo({ top: scrollTop, behavior: 'smooth' })
    }
  }

  function checkVisibility() {
    if (!show || hasBeenShown || !like_panel) return

    const footer = document.getElementById('send-area')
    const footerHeight = footer ? footer.offsetHeight : 0
    const rect = like_panel.getBoundingClientRect()
    const appeared = !like_panel.classList.contains('hidden') && rect.height > 0

    if (appeared) {
      scrollIntoViewWithOffset(like_panel, footerHeight)
      hasBeenShown = true
    } else {
      requestAnimationFrame(checkVisibility)
    }
  }

  $: if (show && !hasBeenShown && like_panel) {
    checkVisibility()
  } else if (!show) {
    hasBeenShown = false
  }
</script>

<div bind:this={like_panel} class="like-panel {show === false ? 'hidden' : ''}">
  <p class="thumb-icon inline-svg">
    <svelte:component this={Icon} />
    <span>{text}</span>
  </p>
  {#each choices as [display_value, internal_value], i}
    <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
    <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
    <label
      class:disabled
      class:selected={value.includes(internal_value)}
      aria-checked={value.includes(internal_value)}
      aria-disabled={disabled ? 'true' : 'false'}
      tabindex="0"
      on:keydown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          toggle_choice(internal_value)
        }
      }}
    >
      <input
        {disabled}
        on:change={() => toggle_choice(internal_value)}
        checked={value.includes(internal_value)}
        type="checkbox"
        name={internal_value?.toString()}
        title={`${display_value} pour le modèle ${model}`}
        aria-checked={value.includes(internal_value)}
      />
      <span class="ml-2" title={`${display_value} pour le modèle ${model}`}>{display_value}</span>
    </label>
  {/each}
  <button {disabled} class:selected={commented} data-fr-opened="false" aria-controls={modalId}>
    Autre…
  </button>
</div>

<style>
  .inline-svg :global(svg) {
    display: inline;
  }

  .like-panel {
    padding: 1em 1.5em 1em;
    background-color: white;
    border-color: #e5e5e5;
    border-style: dashed;
    border-width: 1.5px;
    border-radius: 0.25rem;
  }
  [type='checkbox'] {
    display: none;
  }

  label span {
    margin-left: 0;
  }
  label {
    line-height: 3em;
    padding: 4px 10px;
  }
  label,
  button {
    /* font-size: 0.875em; */
    border-radius: 1.5rem !important;
    background: white;
    color: #606367 !important;
    border: 1px #dadce0 solid !important;
    font-weight: 500;
    margin-right: 10px;
    cursor: pointer;
  }
  button {
    padding: 3px 10px;
  }

  label.selected,
  label:active,
  button:active,
  button.selected {
    background: #f5f5fe !important;
    color: #6a6af4 !important;
    border: 1px #6a6af4 solid !important;
  }

  label:hover,
  button:hover {
    background-color: var(--hover);
  }

  .thumb-icon {
    font-weight: 700;
    color: #3a3a3a;
    margin-bottom: 5px !important;
  }

  label.disabled.selected,
  button[disabled].selected {
    opacity: 0.5;
    box-shadow: none;
    background-color: #eee !important;
    border: 1px solid #606367 !important;
    color: #3a3a3a !important;
  }

  label.disabled:hover,
  button[disabled]:hover {
    cursor: not-allowed;
  }
</style>
