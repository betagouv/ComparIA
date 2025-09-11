<script lang="ts">
  import { Button, Icon } from '$components/dsfr'
  import { negativeReactions, positiveReactions, type ReactionPref } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { noop } from '$lib/utils/commons'

  // TODO: rework

  export interface LikePanelProps {
    show: boolean
    kind: 'like' | 'dislike'
    model: string
    selection: ReactionPref[]
    comment?: string
    modalId?: string
    disabled?: boolean
    mode?: 'react' | 'vote'
    onSelectionChange?: (selection: ReactionPref[]) => void
    onCommentChange?: (comment: string) => void
  }

  let {
    show,
    kind,
    model,
    modalId = undefined,
    selection = $bindable([]),
    comment = $bindable(''),
    disabled = false,
    mode = 'react',
    onSelectionChange = noop,
    onCommentChange = noop
  }: LikePanelProps = $props()

  let like_panel: HTMLDivElement
  let hasBeenShown = $state(false)

  const reactions = {
    like: {
      label: m['vote.choices.positive.question'](),
      icon: 'thumb-up-fill',
      choices: positiveReactions.map((value) => ({
        value,
        label: m[`vote.choices.positive.${value}`]()
      }))
    },
    dislike: {
      label: m['vote.choices.negative.question'](),
      icon: 'thumb-down-fill',
      choices: negativeReactions.map((value) => ({
        value,
        label: m[`vote.choices.negative.${value}`]()
      }))
    }
  }
  const reaction = $derived(reactions[kind])

  function toggle_choice(choice: ReactionPref): void {
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
  <p class="me-3! {mode === 'vote' ? 'mb-0! mt-1!' : 'mb-3!'}">
    <Icon icon={reaction.icon} class="text-primary" />
    <span
      class="text-dark-grey ms-2 text-[14px] font-bold md:text-base"
      class:sr-only={mode === 'vote'}
    >
      {reaction.label}
    </span>
  </p>
  <div class="flex flex-wrap gap-3">
    {#each reaction.choices as { value, label } (value)}
      <label
        class:disabled
        class:selected={selection.includes(value)}
        class="checkbox-btn cg-border bg-white! px-2! md:px-3! py-1! text-[14px]"
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
        class:selected={comment !== ''}
        class="checkbox-btn cg-border bg-white! px-2! md:px-3! py-1! text-[14px]!"
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
    onblur={() => onCommentChange(comment)}
    onkeydown={(e) => {
      if (e.key === 'Escape') {
        onCommentChange(comment)
      }
    }}
  >
    <div class="fr-container fr-container--fluid fr-container-md">
      <div class="fr-grid-row fr-grid-row--center">
        <div class="fr-col-12 fr-col-md-8 fr-col-lg-6">
          <div class="fr-modal__body rounded-xl">
            <div class="fr-modal__header">
              <Button
                variant="tertiary-no-outline"
                text={m['words.close']()}
                title={m['closeModal']()}
                aria-controls={modalId}
                class="fr-btn--close"
                onclick={() => onCommentChange(comment)}
              />
            </div>
            <div class="fr-modal__content">
              <p id="{modalId}-label" class="modal-title">{m['vote.comment.add']()}</p>
              <div>
                <textarea
                  placeholder={m['vote.comment.placeholder']({ model })}
                  class="fr-input"
                  rows="4"
                  bind:value={comment}
                ></textarea>
                <Button
                  aria-controls={modalId}
                  class="mt-8!"
                  onclick={() => onCommentChange(comment)}
                >
                  {m['words.send']()}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </dialog>
{/if}

<style>
  [type='checkbox'] {
    display: none;
  }

  .checkbox-btn {
    display: inline-block;
    border-radius: 1.5rem !important;
    color: #606367 !important;
    font-weight: 500;
    cursor: pointer;
  }

  .checkbox-btn.selected,
  .checkbox-btn:active {
    background: var(--blue-france-975-75) !important;
    color: var(--blue-france-main-525) !important;
    border: 1px var(--blue-france-main-525) solid !important;
  }

  .checkbox-btn:hover {
    background-color: var(--hover);
  }

  .checkbox-btn.disabled.selected,
  button[disabled].checkbox-btn.selected {
    opacity: 0.5;
    box-shadow: none;
    background-color: var(--grey-950-125) !important;
    border: 1px solid #606367 !important;
    color: var(--grey-200-850) !important;
  }

  .checkbox-btn.disabled:hover,
  button[disabled].checkbox-btn:hover {
    cursor: not-allowed;
  }

  .modal-title {
    font-weight: 700;
    font-size: 1.1em;
  }
</style>
