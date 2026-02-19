<script lang="ts">
  import { Button, Icon } from '$components/dsfr'
  import Selector from '$components/Selector.svelte'
  import {
    APINegativeReactions,
    APIPositiveReactions,
    type APIReactionPref
  } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { noop } from '$lib/utils/commons'

  export interface LikePanelProps {
    id: string
    show: boolean
    kind: 'like' | 'dislike'
    model: string
    selection: APIReactionPref[]
    comment?: string
    disabled?: boolean
    mode?: 'react' | 'vote'
    onSelectionChange?: (selection: APIReactionPref[]) => void
    onCommentChange?: (comment: string) => void
  }

  let {
    id,
    show,
    kind,
    model,
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
      choices: APIPositiveReactions.map((value) => ({
        value,
        label: m[`vote.choices.positive.${value}`]()
      })) as { value: APIReactionPref; label: string }[]
    },
    dislike: {
      label: m['vote.choices.negative.question'](),
      icon: 'thumb-down-fill',
      choices: APINegativeReactions.map((value) => ({
        value,
        label: m[`vote.choices.negative.${value}`]()
      })) as { value: APIReactionPref; label: string }[]
    }
  }
  const reaction = $derived(reactions[kind])

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
  <p class="me-3! {mode === 'vote' ? 'mt-1! mb-0!' : 'mb-3!'}">
    <Icon icon={reaction.icon} class="text-primary" />
    <span
      class="ms-2 font-bold text-dark-grey md:text-base text-[14px]"
      class:sr-only={mode === 'vote'}
    >
      {reaction.label}
    </span>
  </p>
  <Selector
    id="{id}-selector"
    kind="checkbox"
    bind:value={selection}
    choices={reaction.choices}
    multiple
    {disabled}
    containerClass="flex flex-wrap gap-3"
    choiceClass="px-2 py-1 md:px-3 text-[14px]! rounded-full! font-medium! text-grey! has-checked:text-primary! border-1! m-0!"
    onChange={onSelectionChange}
  >
    {#snippet extra(props)}
      {#if mode === 'react'}
        <button
          {disabled}
          class={[props.class, comment !== '' ? 'border-primary! text-primary!' : '']}
          data-fr-opened="false"
          aria-controls="{id}-modal"
        >
          {m['vote.choices.other']()}
        </button>
      {/if}
    {/snippet}
  </Selector>
</div>

<!-- Weird way to catch the comment if not validated but modal closed -->
{#if mode === 'react'}
  <dialog
    aria-labelledby="{id}-modal-label"
    id="{id}-modal"
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
                aria-controls="{id}-modal"
                class="fr-btn--close"
                onclick={() => onCommentChange(comment)}
              />
            </div>
            <div class="fr-modal__content">
              <p id="{id}-modal-label" class="modal-title">{m['vote.comment.add']()}</p>
              <div>
                <textarea
                  placeholder={m['vote.comment.placeholder']({ model })}
                  class="fr-input"
                  rows="4"
                  bind:value={comment}
                ></textarea>
                <Button
                  aria-controls="{id}-modal"
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
  .modal-title {
    font-weight: 700;
    font-size: 1.1em;
  }
</style>
