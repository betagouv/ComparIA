<script lang="ts">
  import { Icon } from '$components/dsfr'
  import { type TurnChoice } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { propsToAttrs, sanitize } from '$lib/utils/commons'
  import { onDestroy } from 'svelte'

  interface VoteSelectProps {
    id: string
    onVote: (choice: TurnChoice) => void
  }
  let { id, onVote }: VoteSelectProps = $props()

  const choiceIcons: Record<TurnChoice, string> = {
    a_better: 'i-ri-arrow-left-circle-line',
    b_better: 'i-ri-arrow-right-circle-line',
    both_bad: 'i-ri-thumb-down-line',
    both_good: 'i-ri-thumb-up-line',
    idk: ''
  }
  // Display order, not TURN_CHOICES order. The grid used to be reordered in CSS
  // for narrow screens, which left the tab order zigzagging across it: second
  // stop bottom-right, fourth stop top-right. One order everywhere instead.
  const choices = (['a_better', 'b_better', 'both_bad', 'both_good'] as const).map((value) => ({
    value,
    label: value,
    icon: choiceIcons[value]
  }))

  let pickedChoice = $state<TurnChoice | null>(null)
  let voteTimeout: ReturnType<typeof setTimeout> | undefined

  function onSubmit(e: SubmitEvent) {
    e.preventDefault()
    if (pickedChoice) return
    const choice = e.submitter!.dataset.choice as TurnChoice
    pickedChoice = choice
    voteTimeout = setTimeout(() => onVote(choice), 280)
  }

  onDestroy(() => clearTimeout(voteTimeout))
</script>

<form class="px-1 md:px-4 w-full" novalidate onsubmit={onSubmit}>
  <fieldset
    {id}
    aria-labelledby="{id}-legend {id}-help"
    class="cl-vote-select xl:max-w-[950px] bg-light-primary py-2 px-2 md:px-5 rounded-b-xl shadow-md gap-1 mx-auto flex flex-col"
  >
    <legend id="{id}-legend" class="sr-only">{m['vote.title']()}</legend>

    <div class="gap-1 md:gap-2 md:grid-cols-4 grid grid-cols-2">
      {#each choices as choice (choice.value)}
        <button
          type="submit"
          class={[
            'cl-vote-choice rounded-lg px-1 py-2 md:p-2 text-xs! bg-white cg-border flex items-center',
            { 'cl-vote-picked': pickedChoice === choice.value }
          ]}
          data-choice={choice.value}
          disabled={pickedChoice !== null && pickedChoice !== choice.value}
        >
          <span class={['gap-1 m-auto flex', { 'flex-row-reverse': choice.value === 'b_better' }]}>
            <Icon icon={choice.icon} block size="xs" class="text-primary" />
            {m[`vote.turn.choices.${choice.value}`]()}
          </span>
        </button>
      {/each}
    </div>

    <div class="order-last flex justify-center">
      <button type="submit" class="text-dark-grey text-xs bg-transparent!" data-choice="idk">
        <span class="underline-1 underline">{m[`vote.turn.choices.idk`]()}</span>
      </button>
    </div>

    <!-- hidden, not sr-only, on narrow screens: sr-only kept the link in the
         tab order while parking it off-screen, so focus vanished into nothing.
         It still names the fieldset through aria-labelledby either way. -->
    <p id="{id}-help" class="mb-0! text-grey lh-normal! md:block hidden text-center text-[11px]!">
      {@html sanitize(
        m['vote.turn.important']({
          linkProps: propsToAttrs({
            href: '#',
            'data-fr-opened': 'false',
            'aria-controls': 'fr-modal-vote'
          })
        })
      )}
    </p>
  </fieldset>
</form>

<style>
  .cl-vote-select button {
    &:disabled {
      filter: grayscale(100%);
    }
  }

  .cl-vote-choice {
    transition:
      transform 150ms ease,
      background-color 150ms ease;
  }
  .cl-vote-choice:hover:not(:disabled) {
    transform: scale(1.02);
  }
  .cl-vote-choice:active:not(:disabled) {
    transform: scale(0.97);
  }
  .cl-vote-picked {
    background-color: var(--blue-france-main-525) !important;
    color: white !important;
    transform: scale(1.04);
  }
  .cl-vote-picked :global(.text-primary) {
    color: white !important;
  }

  :global(.cl-vote-nudge) {
    animation: vote-nudge 700ms ease-in-out;
  }

  @keyframes vote-nudge {
    0%,
    100% {
      transform: scale(1);
      box-shadow: 0 2px 6px rgb(0 0 0 / 16%);
    }
    35%,
    65% {
      transform: scale(1.025);
      box-shadow:
        0 0 0 4px var(--blue-france-850-200),
        0 4px 12px rgb(0 0 0 / 20%);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    :global(.cl-vote-nudge) {
      animation: none;
      box-shadow: 0 0 0 4px var(--blue-france-850-200);
    }
  }
</style>
