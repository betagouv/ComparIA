<script lang="ts">
  let {
    onvote,
    disabled = false
  }: {
    onvote: (chosen: 'a' | 'b' | 'tie') => void
    disabled?: boolean
  } = $props()
</script>

<div class="fr-container py-7">
  <div class="text-center mb-6">
    <h4 class="fr-h6 mb-2!">Which result is better?</h4>
    <p class="text-sm text-grey">Vote anonymously — tool identities will be revealed after voting</p>
  </div>

  <div class="flex flex-row gap-4 justify-center flex-wrap">
    <button
      class="px-6 py-3 rounded-lg border border-primary text-primary font-bold hover:bg-primary hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      onclick={() => onvote('a')}
      {disabled}
    >
      A is better
    </button>

    <button
      class="px-6 py-3 rounded-lg border border-grey text-grey font-bold hover:bg-grey hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      onclick={() => onvote('tie')}
      {disabled}
    >
      Tie
    </button>

    <button
      class="px-6 py-3 rounded-lg border border-primary text-primary font-bold hover:bg-primary hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      onclick={() => onvote('b')}
      {disabled}
    >
      B is better
    </button>
  </div>
</div>
