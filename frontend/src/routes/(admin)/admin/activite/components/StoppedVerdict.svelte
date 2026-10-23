<script module lang="ts">
  import type { ActivityStoppedMessage } from '$lib/generated/admin'
  import { m } from '$lib/i18n/messages'

  type Verdict = 'blocked' | 'unavailable' | 'warned' | 'proceeded'

  export function verdictOf(message: ActivityStoppedMessage): Verdict {
    if (message.decision === 'warned') return message.user_proceeded ? 'proceeded' : 'warned'
    return message.decision === 'error' ? 'unavailable' : 'blocked'
  }

  const verdicts: Record<Verdict, { text: () => string; variant: 'red' | 'yellow' | '' }> = {
    blocked: { text: () => m['admin.activity.stopped.verdicts.blocked'](), variant: 'red' },
    unavailable: { text: () => m['admin.activity.stopped.verdicts.unavailable'](), variant: 'red' },
    warned: { text: () => m['admin.activity.stopped.verdicts.warned'](), variant: 'yellow' },
    proceeded: { text: () => m['admin.activity.stopped.verdicts.proceeded'](), variant: '' }
  }
</script>

<script lang="ts">
  import { Badge } from '$components/dsfr'

  let { message }: { message: ActivityStoppedMessage } = $props()

  const verdict = $derived(verdicts[verdictOf(message)])
</script>

<span class="gap-1 flex flex-col items-start">
  <Badge size="sm" noTooltip variant={verdict.variant} text={verdict.text()} />
  {#if message.criteria.length}
    <span class="fr-text--xs mb-0! text-[--text-mention-grey]">{message.criteria.join(', ')}</span>
  {/if}
</span>
