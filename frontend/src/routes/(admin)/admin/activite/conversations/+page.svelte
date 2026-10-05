<script lang="ts">
  import { goto } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import { Alert, Button, Search, Select } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { untrack } from 'svelte'
  import type { ActivityConversationRow } from '$lib/generated/admin'
  import { toRelativeTime } from '$lib/utils/data'
  import { ConversationModal, JourneyTrack, VerdictMark } from '../components'
  import {
    FLAGS,
    JOURNEYS,
    journeyChanges,
    journeyOf,
    label,
    nextQuery,
    sideVerdict,
    stageOf
  } from '../filters'
  import type { PageProps } from './$types'

  let { data }: PageProps = $props()

  const locale = getLocale()
  const numberFormatter = new Intl.NumberFormat(locale)
  const params = $derived(page.url.searchParams)

  function update(changes: Record<string, string | null>) {
    goto(resolve(`/admin/activite/conversations${nextQuery(page.url.searchParams, changes)}`), {
      keepFocus: true,
      noScroll: true
    })
  }

  let search = $derived(params.get('search') ?? '')
  $effect(() => {
    const wanted = search.trim()
    if (wanted === untrack(() => params.get('search') ?? '')) return
    if (wanted.length > 0 && wanted.length < 3) return
    const timeout = setTimeout(() => update({ search: wanted || null }), 400)
    return () => clearTimeout(timeout)
  })

  // Search and journey only. Vote, topic and flag filters still work from
  // the address, for the overview's links and anyone who needs them.
  const journeyOptions = [
    { value: '', label: m['admin.activity.filters.allJourneys']() },
    ...JOURNEYS.map((value) => ({ value, label: label('stages', value) }))
  ]

  let selected = $state<number | null>(null)

  // Icons rather than badges, named in the tooltip and the accessible label.
  const flagIcons: Record<string, string> = {
    pii: 'i-ri-spy-line',
    spam: 'i-ri-spam-2-line',
    error: 'i-ri-error-warning-line',
    archived: 'i-ri-archive-line',
    not_analyzed: 'i-ri-hourglass-line'
  }

  function flagsOf(row: ActivityConversationRow) {
    return FLAGS.filter(
      (flag) =>
        (flag === 'pii' && row.contains_pii) ||
        (flag === 'spam' && row.contains_spam) ||
        (flag === 'error' && row.has_error) ||
        (flag === 'archived' && row.archived && !row.contains_pii && !row.contains_spam) ||
        (flag === 'not_analyzed' && !row.llm_analyzed)
    )
  }

  function detailHref(id: string) {
    return resolve(`/admin/activite/conversations/${id}${page.url.search}`)
  }

  const total = $derived(data.conversations?.total)
</script>

<section
  class="activity-filters gap-x-3 gap-y-2 mb-4 flex flex-wrap items-center"
  aria-label={m['admin.activity.filters.label']()}
>
  <Search
    id="activity-search"
    label={m['admin.activity.filters.search']()}
    placeholder={m['admin.activity.filters.search']()}
    bind:value={search}
    class="min-w-64 mb-0! grow"
  />
  <Select
    id="activity-journey"
    label={m['admin.activity.filters.journey']()}
    hideLabel
    options={journeyOptions}
    selected={journeyOf(params)}
    onchange={(event) => update(journeyChanges(event.currentTarget.value))}
    groupClass="mb-0!"
  />
</section>

{#if !data.conversations}
  <Alert variant="error" title={data.error ?? m['admin.activity.errors.generic']()} />
{:else}
  {#if total != null}
    <p id="activity-conversations-count" class="fr-text--xs mb-2! text-[--text-mention-grey]">
      {data.conversations.total_capped
        ? m['admin.activity.conversations.countCapped']({ count: numberFormatter.format(total) })
        : m['admin.activity.conversations.count']({ count: numberFormatter.format(total) })}
    </p>
  {/if}

  {#if data.conversations.items.length === 0}
    <p class="text-grey">{m['admin.activity.conversations.empty']()}</p>
  {:else}
    <!-- A plain table: rows to skim, not a data grid. A click anywhere on a
         row opens it; the prompt button is the keyboard's way in. -->
    <table class="activity-table w-full">
      <caption class="sr-only">{m['admin.activity.conversations.caption']()}</caption>
      <thead>
        <tr>
          <th scope="col" class="w-28 max-md:hidden">
            {m['admin.activity.conversations.cols.date']()}
          </th>
          <th scope="col">{m['admin.activity.conversations.cols.conversation']()}</th>
          <th scope="col" class="w-56 max-md:hidden">
            {m['admin.activity.conversations.cols.models']()}
          </th>
          <th scope="col" class="w-40 max-md:w-32">
            {m['admin.activity.conversations.cols.journey']()}
          </th>
        </tr>
      </thead>
      <tbody>
        {#each data.conversations.items as row, index (row.id)}
          {@const flags = flagsOf(row)}
          <tr onclick={() => (selected = index)}>
            <td class="max-md:hidden">
              <time
                class="fr-text--xs mb-0! whitespace-nowrap text-[--text-mention-grey]"
                datetime={row.created_at}
              >
                {toRelativeTime(new Date(row.created_at), locale)}
              </time>
            </td>
            <td class="max-w-0">
              <button
                type="button"
                class="fr-text--sm mb-0! block w-full truncate text-start"
                onclick={(event) => {
                  event.stopPropagation()
                  selected = index
                }}
              >
                {#if row.contains_pii}
                  <em class="text-[--text-mention-grey]">
                    {m['admin.activity.conversations.hiddenPrompt']()}
                  </em>
                {:else}
                  {row.first_prompt}
                {/if}
              </button>
              <p
                class="fr-text--xs mb-0! mt-0.5 gap-2 flex items-center text-[--text-mention-grey]"
              >
                {#if row.turns > 1}
                  <span class="whitespace-nowrap">
                    {m['admin.activity.conversations.turnsCount']({ count: row.turns })}
                  </span>
                {/if}
                {#each flags as flag (flag)}
                  <span
                    class={[flagIcons[flag], 'shrink-0']}
                    role="img"
                    aria-label={label('flags', flag)}
                    title={label('flags', flag)}
                  ></span>
                {/each}
                {#if row.comment && !row.contains_pii}
                  <span class="gap-1 min-w-0 flex items-center">
                    <span class="i-ri-chat-quote-line shrink-0" aria-hidden="true"></span>
                    <span class="truncate italic">« {row.comment} »</span>
                  </span>
                {/if}
              </p>
            </td>
            <td class="max-md:hidden">
              {#each ['a', 'b'] as const as side (side)}
                {@const model = side === 'a' ? row.model_a : row.model_b}
                {@const verdict = sideVerdict(row.choices, side)}
                <span class="fr-text--sm mb-0! gap-1.5 flex items-center whitespace-nowrap">
                  <VerdictMark {verdict} />
                  <span
                    class={[
                      'max-w-[12rem] truncate',
                      verdict === 'preferred' ? 'font-bold' : 'text-[--text-mention-grey]'
                    ]}
                  >
                    {model?.name ?? m['admin.activity.conversation.unknownModel']()}
                  </span>
                </span>
              {/each}
            </td>
            <td>
              <JourneyTrack stage={stageOf(row)} />
            </td>
          </tr>
        {/each}
      </tbody>
    </table>

    <ConversationModal rows={data.conversations.items} bind:index={selected} hrefFor={detailHref} />
  {/if}

  <nav class="gap-3 mt-4 flex justify-end" aria-label={m['admin.activity.conversations.caption']()}>
    {#if params.get('cursor')}
      <Button
        variant="secondary"
        size="sm"
        text={m['admin.activity.conversations.first']()}
        onclick={() => update({})}
      />
    {/if}
    {#if data.conversations.next_cursor}
      <Button
        size="sm"
        icon="arrow-right-line"
        iconPos="right"
        text={m['admin.activity.conversations.next']()}
        onclick={() => update({ cursor: data.conversations!.next_cursor })}
      />
    {/if}
  </nav>
{/if}

<style>
  .activity-table {
    border-collapse: collapse;
    table-layout: fixed;
  }
  .activity-table th {
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid var(--border-default-grey);
    color: var(--text-mention-grey);
    font-size: 0.75rem;
    font-weight: 500;
    text-align: start;
  }
  .activity-table td {
    padding: 0.625rem 0.75rem;
    border-bottom: 1px solid var(--border-default-grey);
    vertical-align: middle;
  }
  .activity-table tbody tr {
    cursor: pointer;
  }
  .activity-table tbody tr:hover {
    background-color: var(--background-default-grey-hover);
  }
</style>
