<script lang="ts">
  import { resolve } from '$app/paths'
  import { Badge } from '$components/dsfr'
  import type { AdminPublishDestination, AdminPublishStatus } from '$lib/generated/admin'
  import { m } from '$lib/i18n/messages'
  import { formatDate, runStatus, runVariant } from './format'

  let {
    status,
    destinations
  }: { status: AdminPublishStatus; destinations: AdminPublishDestination[] } = $props()

  const lastRun = $derived(status.runs[0])
  // Every one of them gets the whole reserved pool: a conversation is not
  // reserved for one partner in particular.
  const partners = $derived(
    destinations.filter(
      (destination) => destination.enabled && destination.datasets.includes('reserved')
    )
  )
</script>

<section class="mb-10 gap-4 md:grid-cols-3 grid" aria-label={m['admin.publishing.overview']()}>
  <div class="p-4 rounded-lg cg-border">
    <h2 class="fr-text--sm text-grey mb-2!">{m['admin.publishing.overviewLastRun']()}</h2>
    {#if lastRun}
      <p class="mb-1! gap-2 flex flex-wrap items-center">
        <Badge size="sm" text={runStatus(lastRun)} variant={runVariant(lastRun)} />
        <span class="fr-text--sm mb-0!">
          {formatDate(lastRun.finished_at ?? lastRun.started_at)}
        </span>
      </p>
    {:else}
      <p class="fr-text--sm mb-0!">{m['admin.publishing.lastRunNever']()}</p>
    {/if}
  </div>

  <div class="p-4 rounded-lg cg-border">
    <h2 class="fr-text--sm text-grey mb-2!">{m['admin.publishing.reservedTitle']()}</h2>
    <p class="fr-h4 mb-1!">{status.reserved}</p>
    <p class="fr-text--sm mb-2!">
      {m['admin.publishing.overviewReservedSent']({ sent: status.reserved_sent })}
    </p>
    <a
      class="fr-link fr-text--sm"
      href={resolve('/admin/activite/conversations?period=all&reserved=true')}
    >
      {m['admin.publishing.reservedSee']()}
    </a>
  </div>

  <div class="p-4 rounded-lg cg-border">
    <h2 class="fr-text--sm text-grey mb-2!">{m['admin.publishing.overviewPartners']()}</h2>
    {#if partners.length}
      <ul class="mb-2! ps-0! list-none">
        {#each partners as partner (partner.id)}
          <li class="fr-text--sm mb-0! font-bold">{partner.name}</li>
        {/each}
      </ul>
      <p class="fr-text--xs text-grey mb-0!">{m['admin.publishing.overviewPartnersHelp']()}</p>
    {:else}
      <p class="fr-text--sm text-warning mb-0!">{m['admin.publishing.overviewNoPartner']()}</p>
    {/if}
  </div>
</section>
