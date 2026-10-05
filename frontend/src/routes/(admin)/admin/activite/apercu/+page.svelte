<script lang="ts">
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import { Alert } from '$components/dsfr'
  import { api } from '$lib/fastapi-client'
  import type { ActivityOverview } from '$lib/generated/admin'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import ConversationActivityChart from '$components/ConversationActivityChart.svelte'
  import { BarList, Funnel, StackedBar } from '../components'
  import {
    CHOICES,
    CHOICE_COLORS,
    MODES,
    SHARED_FILTERS,
    errorMessage,
    label,
    nextQuery,
    pick
  } from '../filters'
  import type { PageProps } from './$types'

  let { data }: PageProps = $props()

  // Set by the refresh button, dropped as soon as the filters load new data.
  let refreshed = $state<ActivityOverview | null>(null)
  let refreshing = $state(false)
  let refreshError = $state<string | null>(null)
  $effect(() => {
    void data.overview
    refreshed = null
    refreshError = null
  })
  const overview = $derived(refreshed ?? data.overview)

  async function refresh() {
    refreshing = true
    refreshError = null
    try {
      const searchParams = pick(page.url.searchParams, SHARED_FILTERS)
      searchParams.set('refresh', 'true')
      refreshed = await api.request<ActivityOverview>('/admin/activity/overview', {
        searchParams
      })
    } catch (error) {
      refreshError = errorMessage(error)
    } finally {
      refreshing = false
    }
  }

  const locale = getLocale()
  const numberFormatter = new Intl.NumberFormat(locale)
  const decimalFormatter = new Intl.NumberFormat(locale, { maximumFractionDigits: 1 })
  const percentFormatter = new Intl.NumberFormat(locale, {
    style: 'percent',
    maximumFractionDigits: 1
  })
  const timeFormatter = new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit' })

  const ratio = (count: number, total: number) => (total ? count / total : 0)

  // What the funnel does not say, as a quiet line under it.
  const metrics = $derived.by(() => {
    if (!overview) return []
    const totals = overview.totals
    const ofPrompts = (count: number) =>
      m['admin.activity.overview.ofPrompts']({
        count: numberFormatter.format(count),
        total: numberFormatter.format(totals.prompts)
      })
    const ofConversations = (count: number) =>
      m['admin.activity.overview.ofConversations']({
        count: numberFormatter.format(count),
        total: numberFormatter.format(totals.conversations)
      })
    return [
      {
        id: 'prompts',
        value: numberFormatter.format(totals.prompts),
        label: m['admin.activity.overview.metrics.prompts']()
      },
      {
        id: 'prompts-per-conversation',
        value: decimalFormatter.format(ratio(totals.prompts, totals.conversations)),
        label: m['admin.activity.overview.metrics.promptsPerConversation']()
      },
      {
        id: 'vote-rate',
        value: percentFormatter.format(ratio(totals.votes, totals.prompts)),
        label: m['admin.activity.overview.metrics.voteRate'](),
        help: ofPrompts(totals.votes)
      },
      {
        id: 'comment-rate',
        value: percentFormatter.format(ratio(totals.comments, totals.prompts)),
        label: m['admin.activity.overview.metrics.commentRate'](),
        help: ofPrompts(totals.comments)
      },
      {
        id: 'error-rate',
        value: percentFormatter.format(ratio(totals.errored_conversations, totals.conversations)),
        label: m['admin.activity.overview.metrics.errorRate'](),
        help: ofConversations(totals.errored_conversations)
      }
    ]
  })

  // Each step opens the conversations it counts.
  const shared = $derived(pick(page.url.searchParams, SHARED_FILTERS))
  const listHref = (changes: Record<string, string>) =>
    resolve(`/admin/activite/conversations${nextQuery(shared, changes)}`)

  const funnel = $derived(
    overview
      ? [
          {
            key: 'started',
            label: m['admin.activity.overview.funnel.started'](),
            count: overview.totals.conversations,
            href: listHref({})
          },
          {
            key: 'voted',
            label: m['admin.activity.overview.funnel.voted'](),
            count: overview.totals.voted_conversations,
            href: listHref({ has_vote: 'true' }),
            droppedHref: listHref({ has_vote: 'false' })
          },
          {
            key: 'revealed',
            label: m['admin.activity.overview.funnel.revealed'](),
            count: overview.totals.revealed_conversations,
            href: listHref({ revealed: 'true' }),
            droppedHref: listHref({ has_vote: 'true', revealed: 'false' })
          }
        ]
      : []
  )
  const choices = $derived(
    overview
      ? CHOICES.map((key) => ({
          key,
          label: label('choices', key),
          count: overview.choices[key] ?? 0,
          color: CHOICE_COLORS[key]
        }))
      : []
  )
  const unvoted = $derived(overview?.choices.none ?? 0)
  const modes = $derived(
    overview
      ? MODES.map((key) => ({ key, label: label('modes', key), count: overview.modes[key] ?? 0 }))
      : []
  )
</script>

{#if !overview}
  <Alert variant="error" title={data.error ?? m['admin.activity.errors.generic']()} />
{:else}
  {#if refreshError}
    <Alert variant="error" title={refreshError} class="mb-4" />
  {/if}

  {#if overview.totals.conversations === 0 && overview.totals.prompts === 0}
    <p class="text-grey">{m['admin.activity.overview.empty']()}</p>
  {:else}
    <!-- The journey and the counts around it, side by side: the first screen
         answers "how many, and how far do they get". -->
    <div class="gap-x-10 gap-y-6 lg:grid-cols-[1fr_17rem] grid grid-cols-1" aria-busy={refreshing}>
      <Funnel
        id="activity-funnel"
        title={m['admin.activity.overview.funnelTitle']()}
        steps={funnel}
      />

      <dl class="m-0! p-0! lg:border-s lg:ps-6! flex flex-col border-[--border-default-grey]">
        {#each metrics as metric (metric.id)}
          <div
            id="activity-metric-{metric.id}"
            class="gap-3 py-1.5 flex items-baseline justify-between"
            title={metric.help}
          >
            <dt class="fr-text--xs mb-0! text-[--text-mention-grey]">{metric.label}</dt>
            <dd class="m-0! text-sm font-bold tabular-nums">{metric.value}</dd>
          </div>
        {/each}
      </dl>
    </div>

    <section class="mt-8" aria-labelledby="activity-over-time">
      <h2 id="activity-over-time" class="text-base font-bold mb-1!">
        {m['admin.activity.overview.activityTitle']()}
      </h2>
      <ConversationActivityChart
        compact
        points={overview.activity}
        granularity={overview.bucket}
        rangeStart={(overview.range_start ?? overview.activity[0]?.date ?? '').slice(0, 10)}
        rangeEnd={overview.range_end.slice(0, 10)}
        title={m['admin.activity.overview.activityChartTitle']()}
        labels={{
          table: m['admin.activity.overview.activityTable'](),
          date: m['admin.activity.overview.activityDate'](),
          prompts: m['admin.activity.overview.metrics.prompts'](),
          conversations: m['admin.activity.overview.metrics.conversations'](),
          ongoing: m['statistics.activity.ongoingLabel'](),
          estimate: m['statistics.activity.estimateLabel']()
        }}
      />
    </section>

    <div class="gap-x-10 gap-y-8 mt-8 lg:grid-cols-2 grid grid-cols-1">
      <div>
        <StackedBar
          id="activity-choices"
          title={m['admin.activity.overview.choicesTitle']()}
          segments={choices}
        />
        <p class="fr-text--xs mt-2! mb-0! text-[--text-mention-grey]">
          {m['admin.activity.overview.unvoted']({
            count: numberFormatter.format(unvoted),
            share: percentFormatter.format(ratio(unvoted, overview.totals.prompts))
          })}
        </p>
      </div>
      <BarList id="activity-modes" title={m['admin.activity.overview.modesTitle']()} bars={modes} />
    </div>
  {/if}

  <p class="fr-text--xs mt-8! mb-0! gap-2 flex items-center text-[--text-mention-grey]">
    {m['admin.activity.overview.computedAt']({
      time: timeFormatter.format(new Date(overview.computed_at))
    })}
    <button
      type="button"
      class="gap-1 inline-flex items-center underline"
      disabled={refreshing}
      onclick={refresh}
    >
      <span class="i-ri-refresh-line" aria-hidden="true"></span>
      {m['admin.activity.overview.refresh']()}
    </button>
  </p>
{/if}
