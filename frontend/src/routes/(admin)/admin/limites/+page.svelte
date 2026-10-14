<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { Alert, Badge, Button, Input } from '$components/dsfr'
  import { PageLayout } from '$components/layout'
  import { api, type ApiError } from '$lib/fastapi-client'
  import type {
    AdminLimit,
    AdminLimits,
    AdminLimitsPatch,
    LimitProposal,
    LimitsCalibration
  } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import type { PageProps } from './$types'

  type Name = AdminLimit['name']
  type Draft = Record<Name, string | number | null>

  let { data }: PageProps = $props()

  // Largest value the database column holds.
  const INT_MAX = 2_147_483_647

  const locale = getLocale()
  const numbers = new Intl.NumberFormat(locale)
  const percents = new Intl.NumberFormat(locale, { style: 'percent', maximumFractionDigits: 1 })
  const dates = new Intl.DateTimeFormat(locale, { dateStyle: 'long', timeStyle: 'short' })

  const groups = [
    {
      title: m['admin.limits.groups.all'](),
      names: ['all_per_session', 'all_per_ip']
    },
    {
      title: m['admin.limits.groups.expensive'](),
      names: ['expensive_per_session', 'expensive_per_ip']
    },
    {
      title: m['admin.limits.groups.answer'](),
      names: ['expected_answer_chars']
    }
  ] satisfies { title: string; names: Name[] }[]

  const labels: Record<Name, string> = {
    all_per_session: m['admin.limits.names.all_per_session'](),
    all_per_ip: m['admin.limits.names.all_per_ip'](),
    expensive_per_session: m['admin.limits.names.expensive_per_session'](),
    expensive_per_ip: m['admin.limits.names.expensive_per_ip'](),
    expected_answer_chars: m['admin.limits.names.expected_answer_chars']()
  }
  const helps: Record<Name, string> = {
    all_per_session: m['admin.limits.help.all_per_session'](),
    all_per_ip: m['admin.limits.help.all_per_ip'](),
    expensive_per_session: m['admin.limits.help.expensive_per_session'](),
    expensive_per_ip: m['admin.limits.help.expensive_per_ip'](),
    expected_answer_chars: m['admin.limits.help.expected_answer_chars']()
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

  const changed = $derived(
    data.limits.limits
      .map((limit) => limit.name)
      .filter((name) => draft[name] !== '' && draft[name] !== null)
      .filter((name) => Number(draft[name]) !== byName[name].value)
  )

  function toDraft(limits: AdminLimits): Draft {
    return Object.fromEntries(
      limits.limits.map((limit) => [limit.name, String(limit.value)])
    ) as Draft
  }

  function chars(value: number) {
    return m['admin.limits.unit']({ value: numbers.format(value) })
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

  async function save(patch: AdminLimitsPatch, done: string) {
    saving = true
    try {
      await api.request<AdminLimits>('/admin/limits', {
        method: 'PATCH',
        body: JSON.stringify(patch)
      })
      useToast(done, 4000)
      calibration = null
      await invalidate('admin:limits')
      // The fields show what is stored now.
      draft = toDraft(data.limits)
    } catch (error) {
      useToast((error as Error).message, 6000, 'error')
    } finally {
      saving = false
    }
  }

  async function apply(event: SubmitEvent) {
    event.preventDefault()
    if (!changed.length) {
      useToast(m['admin.limits.nothingToApply'](), 4000)
      return
    }
    await save(
      Object.fromEntries(changed.map((name) => [name, Number(draft[name])])),
      m['admin.limits.applied']()
    )
  }

  function cancel() {
    draft = toDraft(data.limits)
    calibration = null
  }
</script>

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
        {m['admin.limits.calibrate.hint']()}
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

    <form onsubmit={apply} class="gap-8 flex flex-col">
      {#each groups as group, index (index)}
        <section aria-labelledby="limits-group-{index}">
          <h2 id="limits-group-{index}" class="fr-h5 mb-3!">{group.title}</h2>
          <div class="gap-4 md:grid-cols-2 grid grid-cols-1">
            {#each group.names as name (name)}
              {@const limit = byName[name]}
              {@const proposal = proposals[name]}
              <div class="p-4 rounded-lg cg-border flex flex-col">
                <h3 class="fr-h6 mb-1!">{labels[name]}</h3>
                <p class="fr-text--sm mb-3! text-[--text-mention-grey]">{helps[name]}</p>
                <p class="fr-text--sm mb-3! gap-2 flex flex-wrap items-center">
                  <span>{m['admin.limits.current']({ value: chars(limit.value) })}</span>
                  <Badge
                    size="sm"
                    variant={limit.stored ? 'info' : ''}
                    text={limit.stored
                      ? m['admin.limits.isStored']()
                      : m['admin.limits.isDefault']()}
                    noTooltip
                  />
                </p>
                <Input
                  id="limit-{name}"
                  type="number"
                  inputmode="numeric"
                  label={m['admin.limits.newValue']()}
                  bind:value={draft[name] as string}
                  min={name === 'expected_answer_chars' ? 0 : 1}
                  max={INT_MAX}
                  step="1"
                  required
                  groupClass="mb-0!"
                />
                {#if calibration}
                  <div class="proposal mt-3 p-3 rounded-md">
                    {#if proposal}
                      <p class="fr-text--sm mb-1! font-bold">
                        {m['admin.limits.calibrate.proposal']({ value: chars(proposal.value) })}
                      </p>
                      <p class="fr-text--xs mb-0!">{explain(proposal)}</p>
                    {:else}
                      <p class="fr-text--xs mb-0!">{m['admin.limits.calibrate.none']()}</p>
                    {/if}
                  </div>
                {/if}
                {#if limit.stored}
                  <Button
                    variant="tertiary-no-outline"
                    size="sm"
                    text={m['admin.limits.reset']({ value: numbers.format(limit.default) })}
                    disabled={saving}
                    onclick={() => save({ [name]: null }, m['admin.limits.resetDone']())}
                    class="mt-3 self-start"
                  />
                {/if}
              </div>
            {/each}
          </div>
        </section>
      {/each}

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
