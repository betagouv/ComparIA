<script lang="ts">
  import { Button } from '$components/dsfr'
  import type { ActivityConversationRow } from '$lib/generated/admin'
  import { m } from '$lib/i18n/messages'
  import { label } from '../filters'

  let {
    row,
    busy,
    onreserve,
    onunreserve
  }: {
    row: ActivityConversationRow
    busy: boolean
    onreserve: () => void
    onunreserve: () => void
  } = $props()

  const prompt = $derived(
    row.contains_pii ? m['admin.activity.conversations.hiddenPrompt']() : row.first_prompt
  )
</script>

<!-- A comparison that cannot be reserved says why, with no button to
     disable: a disabled button cannot carry a tooltip. -->
{#if row.reserved_at}
  <Button
    size="sm"
    variant="tertiary"
    icon="close-line"
    text={m['admin.activity.reservation.unreserve']()}
    aria-label={m['admin.activity.reservation.unreserveLabel']({ prompt })}
    disabled={busy}
    onclick={onunreserve}
  />
{:else if row.reserve_block}
  <span class="fr-text--xs mb-0! text-[--text-mention-grey]">
    {label('reserveBlocks', row.reserve_block)}
  </span>
{:else}
  <Button
    size="sm"
    variant="secondary"
    icon="lock-line"
    text={m['admin.activity.reservation.reserve']()}
    aria-label={m['admin.activity.reservation.reserveLabel']({ prompt })}
    disabled={busy}
    onclick={onreserve}
  />
{/if}
