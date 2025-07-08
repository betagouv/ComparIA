<script lang="ts">
  import { type Component } from 'svelte'

  export interface LikePanelProps {
    show: boolean
    Icon: Component
    text: string
    choices: [string, string][]
    modalId: string
    onSelectionChange: (selection: string[]) => void
    onCommentChange: (comment: string) => void
    selection?: string[]
    comment?: string
    disabled?: boolean
    model?: string
  }

  let {
    show,
    Icon,
    text,
    choices,
    modalId,
    onSelectionChange,
    onCommentChange,
    selection = [],
    comment = '',
    disabled = false,
    model = ''
  }: LikePanelProps = $props()

  let like_panel: HTMLDivElement
  let hasBeenShown = $state(false)
  let innerComment = $state(comment)

  function toggle_choice(choice: string): void {
    if (selection.includes(choice)) {
      selection = selection.filter((v) => v !== choice)
    } else {
      selection = [...selection, choice]
    }
    onSelectionChange(selection)
  }

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

  $effect(() => {
    if (show && !hasBeenShown && like_panel) {
      checkVisibility()
    } else if (!show) {
      hasBeenShown = false
    }
  })
</script>

<div bind:this={like_panel} class="like-panel {show === false ? 'hidden' : ''}">
  <p class="thumb-icon inline-svg">
    <Icon />
    <span>{text}</span>
  </p>
  {#each choices as [display_value, internal_value], i}
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <label
      class:disabled
      class:selected={selection.includes(internal_value)}
      class="checkbox-btn"
      aria-checked={selection.includes(internal_value)}
      aria-disabled={disabled ? 'true' : 'false'}
      tabindex="0"
      onkeydown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          toggle_choice(internal_value)
        }
      }}
    >
      <input
        {disabled}
        onchange={() => toggle_choice(internal_value)}
        checked={selection.includes(internal_value)}
        type="checkbox"
        name={internal_value?.toString()}
        title={`${display_value} pour le modèle ${model}`}
        aria-checked={selection.includes(internal_value)}
      />
      <span class="ml-2" title={`${display_value} pour le modèle ${model}`}>{display_value}</span>
    </label>
  {/each}
  <button
    {disabled}
    class:selected={innerComment !== ''}
    class="checkbox-btn"
    data-fr-opened="false"
    aria-controls={modalId}
  >
    Autre…
  </button>
</div>

<!-- Weird way to catch the comment if not validated but modal closed -->
<dialog
  aria-labelledby="{modalId}-label"
  id={modalId}
  class="fr-modal"
  onblur={() => onCommentChange(innerComment)}
  onkeydown={(e) => {
    if (e.key === 'Escape') {
      onCommentChange(innerComment)
    }
  }}
>
  <div class="fr-container fr-container--fluid fr-container-md">
    <div class="fr-grid-row fr-grid-row--center">
      <div class="fr-col-12 fr-col-md-8 fr-col-lg-6">
        <div class="fr-modal__body">
          <div class="fr-modal__header">
            <button
              class="fr-btn--close fr-btn"
              title="Fermer la fenêtre modale"
              aria-controls={modalId}
              onclick={() => onCommentChange(innerComment)}>Fermer</button
            >
          </div>
          <div class="fr-modal__content">
            <p id="{modalId}-label" class="modal-title">Ajouter des commentaires</p>
            <div>
              <textarea
                placeholder="Vous pouvez ajouter des précisions sur cette réponse du modèle {model}"
                class="fr-input"
                rows="4"
                bind:value={innerComment}
              ></textarea>
              <button
                aria-controls={modalId}
                class="btn purple-btn"
                onclick={() => onCommentChange(innerComment)}>Envoyer</button
              >
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</dialog>

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
  .checkbox-btn {
    /* font-size: 0.875em; */
    border-radius: 1.5rem !important;
    background: white;
    color: #606367 !important;
    border: 1px #dadce0 solid !important;
    font-weight: 500;
    margin-right: 10px;
    cursor: pointer;
  }
  button.checkbox-btn {
    padding: 3px 10px;
  }

  .checkbox-btn.selected,
  .checkbox-btn:active {
    background: #f5f5fe !important;
    color: #6a6af4 !important;
    border: 1px #6a6af4 solid !important;
  }

  .checkbox-btn:hover {
    background-color: var(--hover);
  }

  .thumb-icon {
    font-weight: 700;
    color: #3a3a3a;
    margin-bottom: 5px !important;
  }

  .checkbox-btn.disabled.selected,
  button[disabled].checkbox-btn.selected {
    opacity: 0.5;
    box-shadow: none;
    background-color: #eee !important;
    border: 1px solid #606367 !important;
    color: #3a3a3a !important;
  }

  .checkbox-btn.disabled:hover,
  button[disabled].checkbox-btn:hover {
    cursor: not-allowed;
  }

  .modal-title {
    font-weight: 700;
    font-size: 1.1em;
  }

  .fr-modal__content .purple-btn {
    float: right;
    margin: 2em 0 !important;
  }
</style>
