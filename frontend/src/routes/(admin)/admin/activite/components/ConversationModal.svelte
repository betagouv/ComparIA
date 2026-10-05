<script lang="ts">
  import { Alert, Button, Modal } from '$components/dsfr'
  import Pending from '$components/Pending.svelte'
  import { api } from '$lib/fastapi-client'
  import type { ActivityConversation, ActivityConversationRow } from '$lib/generated/admin'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { errorMessage, label, stageOf } from '../filters'
  import ConversationSummary from './ConversationSummary.svelte'
  import JourneyTrack from './JourneyTrack.svelte'

  const ID = 'activity-conversation-modal'

  let {
    rows,
    index = $bindable(null),
    hrefFor
  }: {
    rows: ActivityConversationRow[]
    /** The row shown, or null when the pop-up is closed. */
    index: number | null
    hrefFor: (id: string) => string
  } = $props()

  const row = $derived(index === null ? null : (rows[index] ?? null))
  // Kept while the pop-up is open, so stepping back is instant.
  const loaded: Record<string, ActivityConversation> = {}
  let conversation = $state<ActivityConversation | null>(null)
  let error = $state<string | null>(null)

  const dateFormatter = new Intl.DateTimeFormat(getLocale(), {
    dateStyle: 'medium',
    timeStyle: 'short'
  })

  $effect(() => {
    const element = document.getElementById(ID)
    // @ts-expect-error - DSFR is globally available
    if (row && element) window.dsfr(element).modal.disclose()
  })

  // Depends on the row id alone: reading `conversation` here as well would
  // make every answer that lands start the effect, and the fetch, again.
  $effect(() => {
    const id = row?.id
    if (!id) return
    const cached = loaded[id]
    conversation = cached ?? null
    error = null
    if (cached) return
    let stale = false
    api
      .request<ActivityConversation>(`/admin/activity/conversations/${id}`)
      .then((result) => {
        loaded[id] = result
        if (!stale) conversation = result
      })
      .catch((err) => {
        if (!stale) error = errorMessage(err)
      })
    return () => {
      stale = true
    }
  })

  function step(offset: number) {
    if (index === null) return
    const next = index + offset
    if (next >= 0 && next < rows.length) index = next
  }

  function onkeydown(event: KeyboardEvent) {
    // Left and right step through the list while the pop-up is open, unless a
    // field has the keys.
    if (index === null) return
    if ((event.target as HTMLElement).closest('input, textarea, select')) return
    if (event.key === 'ArrowRight') step(1)
    if (event.key === 'ArrowLeft') step(-1)
  }
</script>

<svelte:window {onkeydown} />

<Modal
  id={ID}
  titleId="{ID}-title"
  sizeClass="fr-col-12 fr-col-lg-10"
  onClose={() => (index = null)}
>
  {#if row}
    <div class="gap-1 mb-3 flex items-center">
      <Button
        size="sm"
        variant="tertiary-no-outline"
        icon="arrow-left-s-line"
        iconOnly
        text={m['admin.activity.conversations.previous']()}
        disabled={index === 0}
        onclick={() => step(-1)}
      />
      <span class="fr-text--xs mb-0! text-[--text-mention-grey] tabular-nums">
        {(index ?? 0) + 1} / {rows.length}
      </span>
      <Button
        size="sm"
        variant="tertiary-no-outline"
        icon="arrow-right-s-line"
        iconOnly
        text={m['admin.activity.conversations.nextOne']()}
        disabled={index === rows.length - 1}
        onclick={() => step(1)}
      />
      <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- resolved by the caller -->
      <a href={hrefFor(row.id)} class="fr-link fr-link--sm ms-3">
        {m['admin.activity.conversations.open']()}
      </a>
    </div>

    <!-- The first question opens the conversation just below. -->
    <h2 id="{ID}-title" class="sr-only">
      {row.contains_pii ? m['admin.activity.conversation.title']() : row.first_prompt}
    </h2>
    <p
      class="fr-text--xs mb-6! gap-x-2 gap-y-1 flex flex-wrap items-center text-[--text-mention-grey]"
    >
      <span>{dateFormatter.format(new Date(row.created_at))}</span>
      <span aria-hidden="true">·</span>
      <span>{label('modes', row.mode)}</span>
      {#if row.categories.length}
        <span aria-hidden="true">·</span>
        <span>{row.categories.join(', ')}</span>
      {/if}
      <span aria-hidden="true">·</span>
      <JourneyTrack stage={stageOf(row)} />
    </p>

    {#if error}
      <Alert variant="error" title={error} small />
    {:else if conversation && conversation.id === row.id}
      {#key conversation.id}
        <ConversationSummary {conversation} />
      {/key}
    {:else}
      <Pending />
    {/if}
  {:else}
    <h2 id="{ID}-title" class="sr-only">{m['admin.activity.conversation.title']()}</h2>
  {/if}
</Modal>
