<script lang="ts">
  import { m } from '$lib/i18n/messages'
  import ThumbDownActive from '$lib/icons/ThumbDownActive.svelte'
  import ThumbUpActive from '$lib/icons/ThumbUpActive.svelte'
  import { noop } from '$lib/utils/commons'

  export interface LikePanelProps {
    show: boolean
    kind: 'like' | 'dislike'
    model: string
    onSelectionChange: (selection: string[]) => void
    onCommentChange?: (comment: string) => void
    modalId?: string
    selection?: string[]
    comment?: string
    disabled?: boolean
    mode?: 'react' | 'vote'
  }

  let {
    show,
    kind,
    model,
    onSelectionChange,
    onCommentChange = noop,
    modalId = undefined,
    selection = [],
    comment = '',
    disabled = false,
    mode = 'react'
  }: LikePanelProps = $props()

  let like_panel: HTMLDivElement
  let hasBeenShown = $state(false)
  let innerComment = $state(comment)

  const reactions = {
    like: {
      label: m['vote.choices.positive.question'](),
      Icon: ThumbUpActive,
      choices: (['useful', 'complete', 'creative', 'clear-formatting'] as const).map((value) => ({
        value,
        label: m[`vote.choices.positive.${value}`]()
      }))
    },
    dislike: {
      label: m['vote.choices.negative.question'](),
      Icon: ThumbDownActive,
      choices: (['incorrect', 'superficial', 'instructions-not-followed'] as const).map(
        (value) => ({
          value,
          label: m[`vote.choices.negative.${value}`]()
        })
      )
    }
  }
  const reaction = $derived(reactions[kind])

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

<div
  bind:this={like_panel}
  class="like-panel"
  class:hidden={show === false}
  class:flex={mode === 'vote'}
>
  <p class="thumb-icon me-3! {mode === 'vote' ? 'mb-0! mt-1!' : 'mb-3!'}">
    <reaction.Icon />
    <span class="ms-2" class:sr-only={mode === 'vote'}>{reaction.label}</span>
  </p>
  <div class="flex flex-wrap gap-3">
    {#each reaction.choices as { value, label } (value)}
      <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
      <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
      <label
        class:disabled
        class:selected={selection.includes(value)}
        class="checkbox-btn"
        aria-checked={selection.includes(value)}
        aria-disabled={disabled ? 'true' : 'false'}
        tabindex="0"
        onkeydown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            toggle_choice(value)
          }
        }}
      >
        <input
          {disabled}
          onchange={() => toggle_choice(value)}
          checked={selection.includes(value)}
          type="checkbox"
          name={value?.toString()}
          aria-checked={selection.includes(value)}
        />
        <span title={m['vote.choices.altText']({ choice: label, model })}>{label}</span>
      </label>
    {/each}
    {#if mode === 'react'}
      <button
        {disabled}
        class:selected={innerComment !== ''}
        class="checkbox-btn"
        data-fr-opened="false"
        aria-controls={modalId}
      >
        Autre…
      </button>
    {/if}
  </div>
</div>

<!-- Weird way to catch the comment if not validated but modal closed -->
{#if mode === 'react'}
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
                title={m['closeModal']()}
                aria-controls={modalId}
                onclick={() => onCommentChange(innerComment)}
              >
                {m['words.close']()}
              </button>
            </div>
            <div class="fr-modal__content">
              <p id="{modalId}-label" class="modal-title">{m['vote.comment.add']()}</p>
              <div>
                <textarea
                  placeholder={m['vote.comment.placeholder']({ model })}
                  class="fr-input"
                  rows="4"
                  bind:value={innerComment}
                ></textarea>
                <button
                  aria-controls={modalId}
                  class="btn purple-btn"
                  onclick={() => onCommentChange(innerComment)}
                >
                  {m['words.send']()}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </dialog>
{/if}

<style>
  .thumb-icon {
    font-weight: 700;
    color: #3a3a3a;
  }
  .thumb-icon :global(svg) {
    display: inline;
  }

  [type='checkbox'] {
    display: none;
  }

  label.checkbox-btn {
    padding: 4px 10px;
  }
  .checkbox-btn {
    display: inline-block;
    border-radius: 1.5rem !important;
    background: white;
    color: #606367 !important;
    border: 1px #dadce0 solid !important;
    font-weight: 500;
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
