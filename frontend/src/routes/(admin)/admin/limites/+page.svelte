<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { Accordion, Alert, Badge, Button, Input } from '$components/dsfr'
  import { PageLayout } from '$components/layout'
  import { usdFormatter } from '$lib/currency'
  import { api, type ApiError } from '$lib/fastapi-client'
  import type {
    AdminLimit,
    AdminLimits,
    AdminLimitsPatch,
    LimitProposal,
    LimitsCalibration,
    PriceCheck
  } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { TodayUsage } from './components'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import type { PageProps } from './$types'

  type Name = AdminLimit['name']
  type Draft = Record<Name, string | number | null>

  let { data }: PageProps = $props()

  // Largest value the database column holds.
  const INT_MAX = 2_147_483_647
  // Largest value the API takes in dollars.
  const USD_MAX = 1_000_000

  // Characters, dollars, dollars per million output tokens, or messages.
  type Unit = 'chars' | 'usd' | 'price' | 'count'
  function unit(name: Name): Unit {
    if (name === 'expensive_price_out') return 'price'
    if (name === 'in_flight_per_network') return 'count'
    return name.startsWith('expensive_') ? 'usd' : 'chars'
  }

  const locale = getLocale()
  const numbers = new Intl.NumberFormat(locale)
  const percents = new Intl.NumberFormat(locale, { style: 'percent', maximumFractionDigits: 1 })
  const dollars = usdFormatter(locale)
  const dates = new Intl.DateTimeFormat(locale, { dateStyle: 'long', timeStyle: 'short' })

  // What an admin sets first, then the engine settings, folded away.
  const groups = [
    {
      title: m['admin.limits.groups.all'](),
      names: ['all_per_session', 'all_per_ip']
    },
    {
      title: m['admin.limits.groups.expensive'](),
      names: ['expensive_price_out', 'expensive_per_session', 'expensive_per_ip']
    }
  ] satisfies { title: string; names: Name[] }[]
  const technical: Name[] = ['expected_answer_chars', 'in_flight_per_network']

  const labels: Record<Name, string> = {
    all_per_session: m['admin.limits.names.all_per_session'](),
    all_per_ip: m['admin.limits.names.all_per_ip'](),
    expensive_per_session: m['admin.limits.names.expensive_per_session'](),
    expensive_per_ip: m['admin.limits.names.expensive_per_ip'](),
    expensive_price_out: m['admin.limits.names.expensive_price_out'](),
    expected_answer_chars: m['admin.limits.names.expected_answer_chars'](),
    in_flight_per_network: m['admin.limits.names.in_flight_per_network']()
  }
  const helps: Record<Name, string> = {
    all_per_session: m['admin.limits.help.all_per_session'](),
    all_per_ip: m['admin.limits.help.all_per_ip'](),
    expensive_per_session: m['admin.limits.help.expensive_per_session'](),
    expensive_per_ip: m['admin.limits.help.expensive_per_ip'](),
    expensive_price_out: m['admin.limits.help.expensive_price_out'](),
    expected_answer_chars: m['admin.limits.help.expected_answer_chars'](),
    in_flight_per_network: m['admin.limits.help.in_flight_per_network']()
  }

  const byName = $derived(
    Object.fromEntries(data.limits.limits.map((limit) => [limit.name, limit])) as Record<
      Name,
      AdminLimit
    >
  )

  // svelte-ignore state_referenced_locally
  let draft = $state<Draft>(toDraft(data.limits))
  let calibration = $state<LimitsCalibration | null>(null)
  let calibrating = $state(false)
  let calibrationError = $state<string | null>(null)
  let saving = $state(false)

  const proposals = $derived(
    Object.fromEntries(
      (calibration?.proposals ?? []).map((proposal) => [proposal.name, proposal])
    ) as Partial<Record<Name, LimitProposal>>
  )

  // The models the threshold being typed makes expensive, the one in force
  // while the field is empty.
  const expensiveLLMs = $derived.by(() => {
    const typed = draft.expensive_price_out
    const threshold =
      typed === '' || typed === null ? byName.expensive_price_out.value : Number(typed)
    return data.limits.llms.filter((llm) => llm.price_out > 0 && llm.price_out >= threshold)
  })

  // The proposed daily caps that would change a model's cap.
  const changedCaps = $derived(
    (calibration?.daily_caps ?? []).filter(
      (cap) => data.usage?.find((llm) => llm.llm_id === cap.llm_id)?.cap_usd !== cap.value
    )
  )

  // The values put back on their default: sent as null on "Appliquer", so
  // they follow the default again, as long as the field still holds it.
  let toDefault = $state<Name[]>([])
  const resets = $derived(toDefault.filter((name) => Number(draft[name]) === byName[name].default))

  const changed = $derived(
    data.limits.limits
      .map((limit) => limit.name)
      .filter((name) => draft[name] !== '' && draft[name] !== null)
      .filter((name) => Number(draft[name]) !== byName[name].value || resets.includes(name))
  )

  function toDraft(limits: AdminLimits): Draft {
    return Object.fromEntries(
      limits.limits.map((limit) => [limit.name, String(limit.value)])
    ) as Draft
  }

  function shown(name: Name, value: number) {
    switch (unit(name)) {
      case 'usd':
        return dollars.format(value)
      case 'price':
        return m['admin.limits.unitPrice']({ value: dollars.format(value) })
      case 'count':
        return m['admin.limits.unitCount']({ value: numbers.format(value) })
      default:
        return m['admin.limits.unit']({ value: numbers.format(value) })
    }
  }

  // What a value lets through, in messages of a typical cost, once
  // "Calibrer" has read what a message costs.
  function inMessages(name: Name, value: number): string | undefined {
    const per = name.endsWith('_per_session')
      ? 'session'
      : name.endsWith('_per_ip')
        ? 'network'
        : undefined
    const cost = name.startsWith('expensive_')
      ? calibration?.message_usd
      : calibration?.message_chars
    if (!per || !cost) return undefined
    const count = numbers.format(Math.floor(value / cost))
    return m[`admin.limits.messages.${per}`]({ count })
  }

  // The typed value, spelled out with its unit, under the field.
  function typed(name: Name): string | undefined {
    const value = draft[name]
    if (value === '' || value === null || !Number.isFinite(Number(value))) return undefined
    return shown(name, Number(value))
  }

  const newValueLabels: Record<Unit, string> = {
    chars: m['admin.limits.newValue'](),
    usd: m['admin.limits.newValueUsd'](),
    price: m['admin.limits.newValuePrice'](),
    count: m['admin.limits.newValueCount']()
  }

  function expensiveText(llms: { name: string }[]) {
    const names = llms.map((llm) => llm.name).join(', ')
    if (llms.length > 1) {
      return m['admin.limits.expensiveList']({ count: String(llms.length), names })
    }
    return llms.length
      ? m['admin.limits.expensiveOne']({ names })
      : m['admin.limits.expensiveNone']()
  }

  function priceIssue(check: PriceCheck) {
    return m[`admin.limits.prices.issues.${check.issue}`]()
  }

  function explain(proposal: LimitProposal) {
    const percentile = String(proposal.percentile)
    const count = numbers.format(proposal.sample)
    if (proposal.name === 'expected_answer_chars') {
      return m['admin.limits.calibrate.explain.answer']({
        value: numbers.format(proposal.value),
        count
      })
    }
    if (proposal.name.endsWith('_per_ip')) {
      return m['admin.limits.calibrate.explain.network']({
        size: String(proposal.class_size ?? ''),
        percentile,
        share: percents.format(proposal.over_share ?? 0)
      })
    }
    return proposal.messages != null
      ? m['admin.limits.calibrate.explain.sessionMessages']({
          percentile,
          count,
          messages: numbers.format(proposal.messages)
        })
      : m['admin.limits.calibrate.explain.session']({ percentile, count })
  }

  async function calibrate() {
    calibrating = true
    calibrationError = null
    try {
      calibration = await api.request<LimitsCalibration>('/admin/limits/calibration')
      // Shown in the fields, to apply as they are or to adjust first.
      for (const proposal of calibration.proposals) draft[proposal.name] = String(proposal.value)
    } catch (error) {
      calibration = null
      calibrationError =
        (error as ApiError).detail === 'activity_query_timeout'
          ? m['admin.limits.calibrate.timeout']()
          : m['admin.limits.calibrate.failed']()
    } finally {
      calibrating = false
    }
  }

  /** Store `patch`; false when the server refused it. */
  async function save(patch: AdminLimitsPatch, done: string): Promise<boolean> {
    saving = true
    try {
      await api.request<AdminLimits>('/admin/limits', {
        method: 'PATCH',
        body: JSON.stringify(patch)
      })
      useToast(done, 4000)
      await invalidate('admin:limits')
      return true
    } catch (error) {
      useToast((error as Error).message, 6000, 'error')
      return false
    } finally {
      saving = false
    }
  }

  // Like any other edit, it waits for "Appliquer".
  function reset(name: Name) {
    draft[name] = String(byName[name].default)
    if (!toDefault.includes(name)) toDefault = [...toDefault, name]
  }

  async function apply(event: SubmitEvent) {
    event.preventDefault()
    if (!changed.length && !changedCaps.length) {
      useToast(m['admin.limits.nothingToApply'](), 4000)
      return
    }
    const patch: AdminLimitsPatch = Object.fromEntries(
      changed.map((name) => [name, resets.includes(name) ? null : Number(draft[name])])
    )
    if (changedCaps.length) {
      patch.daily_usd_caps = Object.fromEntries(changedCaps.map((cap) => [cap.llm_id, cap.value]))
    }
    if (await save(patch, m['admin.limits.applied']())) {
      calibration = null
      toDefault = []
      // The fields show what is stored now.
      draft = toDraft(data.limits)
    }
  }

  function cancel() {
    draft = toDraft(data.limits)
    calibration = null
    toDefault = []
  }
</script>

{#snippet card(name: Name)}
  {@const limit = byName[name]}
  {@const proposal = proposals[name]}
  {@const kind = unit(name)}
  {@const messages = inMessages(name, limit.value)}
  <div class={['p-4 rounded-lg cg-border flex flex-col', { 'md:col-span-2': kind === 'price' }]}>
    <h3 class="fr-h6 mb-1!">{labels[name]}</h3>
    <p class="fr-text--sm mb-3! text-[--text-mention-grey]">{helps[name]}</p>
    <p class="fr-text--sm mb-3! gap-2 flex flex-wrap items-center">
      <span>{m['admin.limits.current']({ value: shown(name, limit.value) })}</span>
      <Badge
        size="sm"
        variant={limit.stored ? 'info' : ''}
        text={limit.stored ? m['admin.limits.isStored']() : m['admin.limits.isDefault']()}
        noTooltip
      />
      {#if messages}
        <span class="basis-full">{messages}</span>
      {/if}
    </p>
    <Input
      id="limit-{name}"
      type="number"
      inputmode={kind === 'chars' || kind === 'count' ? 'numeric' : 'decimal'}
      label={newValueLabels[kind]}
      hint={typed(name)}
      bind:value={draft[name] as string}
      min={kind === 'usd'
        ? 0.01
        : kind === 'count' || name === 'all_per_session' || name === 'all_per_ip'
          ? 1
          : 0}
      max={kind === 'chars' || kind === 'count' ? INT_MAX : USD_MAX}
      step={kind === 'chars' || kind === 'count' ? '1' : '0.01'}
      required
      groupClass="mb-0!"
    />
    {#if kind === 'price'}
      <p class="fr-text--sm mt-3! mb-0!" aria-live="polite">
        {expensiveText(expensiveLLMs)}
      </p>
    {/if}
    {#if calibration}
      <div class="proposal mt-3 p-3 rounded-md">
        {#if proposal}
          <p class="fr-text--sm mb-1! font-bold">
            {m['admin.limits.calibrate.proposal']({
              value: shown(name, proposal.value)
            })}
          </p>
          <p class="fr-text--xs mb-0!">{explain(proposal)}</p>
          {#if proposal.few}
            <p class="fr-text--xs mb-0! mt-1! font-bold">
              {m['admin.limits.calibrate.few']()}
            </p>
          {/if}
        {:else if kind === 'price'}
          <p class="fr-text--xs mb-0!">{m['admin.limits.thresholdKept']()}</p>
        {:else if kind === 'count'}
          <p class="fr-text--xs mb-0!">{m['admin.limits.inFlightKept']()}</p>
        {:else}
          <p class="fr-text--xs mb-0!">{m['admin.limits.calibrate.none']()}</p>
        {/if}
      </div>
    {/if}
    {#if limit.stored && !resets.includes(name)}
      <Button
        variant="tertiary-no-outline"
        size="sm"
        text={m['admin.limits.reset']({ value: shown(name, limit.default) })}
        disabled={saving}
        onclick={() => reset(name)}
        class="mt-3 -ms-3 self-start"
      />
    {/if}
  </div>
{/snippet}

<PageLayout
  seoTitle={m['admin.limits.title']()}
  title={m['admin.limits.title']()}
  subtitle={m['admin.limits.subtitle']()}
>
  <div class="gap-6 flex max-w-[880px] flex-col">
    {#if data.limits.updated_at}
      {@const date = dates.format(new Date(data.limits.updated_at))}
      <p class="fr-text--sm mb-0! text-[--text-mention-grey]">
        {data.limits.updated_by
          ? m['admin.limits.updated']({ date, who: data.limits.updated_by })
          : m['admin.limits.updatedUnknown']({ date })}
      </p>
    {/if}

    <section class="p-4 gap-3 md:flex-row md:items-center rounded-lg cg-border flex flex-col">
      <Button
        variant="secondary"
        text={calibrating
          ? m['admin.limits.calibrate.running']()
          : m['admin.limits.calibrate.button']()}
        disabled={calibrating || saving}
        aria-describedby="limits-calibrate-hint"
        onclick={calibrate}
        class="shrink-0"
      />
      <p id="limits-calibrate-hint" class="fr-text--sm mb-0!">
        {m['admin.limits.calibrate.hint']({ days: String(data.limits.calibration_days) })}
      </p>
    </section>

    <div aria-live="polite" class="empty:hidden">
      {#if calibrationError}
        <Alert variant="error" title={calibrationError} small />
      {:else if calibration}
        <p class="fr-text--sm mb-0!">
          {calibration.proposals.length
            ? m['admin.limits.calibrate.sample']({
                comparisons: numbers.format(calibration.comparisons),
                turns: numbers.format(calibration.turns),
                days: String(calibration.days)
              })
            : m['admin.limits.calibrate.empty']()}
          {#if calibration.capped}
            {m['admin.limits.calibrate.capped']()}
          {/if}
        </p>
      {/if}
    </div>

    {#if calibration}
      <section aria-labelledby="limits-prices" class="p-4 rounded-lg cg-border">
        <h2 id="limits-prices" class="fr-h6 mb-1!">{m['admin.limits.prices.title']()}</h2>
        {#if calibration.price_checks.length}
          <p class="fr-text--sm mb-3! text-[--text-mention-grey]">
            {m['admin.limits.prices.intro']()}
          </p>
          <ul class="fr-text--sm mb-0!">
            {#each calibration.price_checks as check (check.id)}
              <li>
                <a href={resolve(`/admin/llms/llms/${check.id}`)}>
                  {m['admin.limits.prices.line']({
                    name: check.name,
                    in: dollars.format(check.price_in),
                    out: dollars.format(check.price_out)
                  })}
                </a>
                {priceIssue(check)}
              </li>
            {/each}
          </ul>
        {:else}
          <p class="fr-text--sm mb-0!">{m['admin.limits.prices.none']()}</p>
        {/if}
      </section>
    {/if}

    <form onsubmit={apply} class="gap-8 flex flex-col">
      {#each groups as group, index (index)}
        <section aria-labelledby="limits-group-{index}">
          <h2 id="limits-group-{index}" class="fr-h5 mb-3!">{group.title}</h2>
          <div class="gap-4 md:grid-cols-2 grid grid-cols-1">
            {#each group.names as name (name)}
              {@render card(name)}
            {/each}
          </div>
        </section>
      {/each}

      <Accordion id="limits-technical" label={m['admin.limits.groups.technical']()} level={2}>
        <div class="gap-4 md:grid-cols-2 grid grid-cols-1">
          {#each technical as name (name)}
            {@render card(name)}
          {/each}
        </div>
      </Accordion>

      <TodayUsage usage={data.usage} proposals={calibration?.daily_caps} />

      {#if changedCaps.length}
        <p class="fr-text--sm mb-0!" aria-live="polite">
          {changedCaps.length > 1
            ? m['admin.limits.today.capsApplied']({ count: String(changedCaps.length) })
            : m['admin.limits.today.capsAppliedOne']()}
        </p>
      {/if}

      <div class="gap-3 flex flex-wrap">
        <Button
          type="submit"
          text={saving ? m['admin.limits.applying']() : m['admin.limits.apply']()}
          disabled={saving}
        />
        <Button
          variant="secondary"
          text={m['admin.limits.cancel']()}
          disabled={saving || (!changed.length && !calibration)}
          onclick={cancel}
        />
      </div>
    </form>
  </div>
</PageLayout>

<style>
  .proposal {
    background-color: var(--background-contrast-info);
  }
</style>
