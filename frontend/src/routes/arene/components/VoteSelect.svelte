<script lang="ts">
  import { Icon } from '$components/dsfr'
  import { TURN_CHOICES, type TurnChoice } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { propsToAttrs, sanitize } from '$lib/utils/commons'

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
  const choices = TURN_CHOICES.filter((v) => v !== 'idk').map((value) => ({
    value,
    label: value,
    icon: choiceIcons[value]
  }))

  function onSubmit(e: SubmitEvent) {
    e.preventDefault()
    onVote(e.submitter!.dataset.choice as TurnChoice)
  }
</script>

<form class="px-4 w-full" novalidate onsubmit={onSubmit}>
  <fieldset
    {id}
    aria-labelledby="{id}-legend {id}-help"
    class="cl-vote-select xl:max-w-[950px] bg-light-info py-2 px-5 rounded-b-xl shadow-md gap-1 mx-auto flex flex-col"
  >
    <legend id="display-fieldset-legend" class="sr-only">{m['vote.title']()}</legend>

    <div class="gap-2 md:grid-cols-4 grid">
      {#each choices as choice (choice.value)}
        <button
          type="submit"
          class="rounded-lg p-2 text-xs! bg-white cg-border flex items-center"
          data-choice={choice.value}
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

    <p id="{id}-help" class="mb-0! text-grey lh-normal! text-center text-[11px]!">
      {@html sanitize(
        m['vote.turn.important']({
          linkProps: propsToAttrs({ href: 'FIXME' })
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
</style>
