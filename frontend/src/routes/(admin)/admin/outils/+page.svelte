<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { Button, Table, Toggle } from '$components/dsfr'
  import Link from '$components/dsfr/Link.svelte'
  import { api } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import type { OrderingMethod, TableCol } from '$lib/utils/data'
  import { sortRows, toSearchString } from '$lib/utils/data'

  import type { PageProps } from './$types'
  import type { ToolHealth } from './+page'

  let { data }: PageProps = $props()
  const baseRoute = '/admin/outils' as const

  const healthLabels = {
    no_credential: m['admin.tools.list.health.no_credential'],
    no_url: m['admin.tools.list.health.no_url'],
    invalid_credential: m['admin.tools.list.health.invalid_credential'],
    no_credit: m['admin.tools.list.health.no_credit'],
    unreachable: m['admin.tools.list.health.unreachable'],
    timeout: m['admin.tools.list.health.timeout'],
    unknown_builtin: m['admin.tools.list.health.unknown_builtin']
  }
  const healthDetails = {
    no_credential: m['admin.tools.errors.no_credential'],
    no_url: m['admin.tools.errors.no_url'],
    invalid_credential: m['admin.tools.errors.invalid_credential'],
    no_credit: m['admin.tools.errors.no_credit'],
    unreachable: m['admin.tools.errors.unreachable'],
    timeout: m['admin.tools.errors.timeout'],
    unknown_builtin: m['admin.tools.errors.unknown_builtin']
  }

  const tools = $derived(
    data.tools.map((tool) => {
      const usage = data.usage.find((u) => u.id === tool.id)
      return {
        ...tool,
        id: tool.id!,
        address: tool.kind === 'mcp' ? (tool.url ?? '') : m['admin.tools.list.builtin'](),
        calls: usage?.calls ?? 0,
        failures: usage?.failures ?? 0,
        // The column needs a key; its cells come from the health check.
        health: 0,
        enabled: tool.enabled ?? false,
        search: toSearchString([tool.label, tool.key, tool.url ?? '', tool.description ?? ''])
      }
    })
  )
  type DataKey = keyof (typeof tools)[number]
  const cols = [
    { id: 'label', label: m['admin.tools.list.label'](), orderable: true },
    { id: 'health', label: m['admin.tools.list.health.title']() },
    { id: 'calls', label: m['admin.tools.list.calls'](), kind: 'number', orderable: true },
    { id: 'enabled', label: m['admin.tools.list.enabled'](), orderable: true }
  ] satisfies TableCol<DataKey>[]
  type ColKey = (typeof cols)[number]['id']

  let orderingCol = $state<ColKey>('label')
  let orderingMethod = $state<OrderingMethod>('descending')
  let search = $state('')

  const sortedRows = $derived(
    sortRows(tools, cols, { col: orderingCol, method: orderingMethod, search })
  )

  // A recheck replaces what the page loaded with; until then, the load's.
  let rechecked = $state<Promise<ToolHealth[]>>()
  const health = $derived(rechecked ?? data.health)
  let rechecking = $state(false)

  async function recheck() {
    rechecking = true
    rechecked = api.request<ToolHealth[]>('/admin/tools/health', {
      searchParams: { refresh: 'true' }
    })
    try {
      await rechecked
    } finally {
      rechecking = false
    }
  }

  // What the switch shows while its request is out, so it moves on click.
  let pending = $state<Record<string, boolean>>({})

  async function setEnabled(tool: { id: string; label: string }, enabled: boolean) {
    pending[tool.id] = enabled
    try {
      await api.request(`/admin/tools/tool/${tool.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ enabled })
      })
      await invalidate('admin:tools')
      useToast(
        enabled
          ? m['admin.tools.list.switchedOn']({ label: tool.label })
          : m['admin.tools.list.switchedOff']({ label: tool.label }),
        4000,
        'success'
      )
    } catch (error) {
      useToast((error as Error).message, 6000, 'error')
    } finally {
      delete pending[tool.id]
    }
  }
</script>

<p class="mb-6! max-w-[700px] text-[--text-mention-grey]">{m['admin.tools.list.intro']()}</p>

<Table
  bind:search
  bind:orderingMethod
  bind:orderingCol
  caption={m['admin.nav.tools']()}
  hideCaption
  {cols}
  rows={sortedRows}
>
  {#snippet headerLeft()}
    <div class="gap-2 flex flex-wrap">
      <Link
        button
        icon="add-line"
        text={m['admin.tools.list.add']()}
        href={resolve(`${baseRoute}/create`)}
      />
      <Button
        variant="secondary"
        icon="refresh-line"
        text={rechecking ? m['admin.tools.list.rechecking']() : m['admin.tools.list.recheck']()}
        disabled={rechecking}
        onclick={recheck}
      />
    </div>
  {/snippet}

  {#snippet cell(tool, col)}
    {#if col.id === 'label'}
      <a href={resolve(`${baseRoute}/${tool.id}`)} class="font-bold">{tool.label}</a>
      <span class="fr-text--xs mb-0! block break-all text-[--text-mention-grey]">
        {tool.address}
      </span>
    {:else if col.id === 'health'}
      {#await health}
        <span class="gap-2 fr-text--sm mb-0! inline-flex items-center text-[--text-mention-grey]">
          <span class="health-dot checking" aria-hidden="true"></span>
          {m['admin.tools.list.health.checking']()}
        </span>
      {:then list}
        {@const result = list.find((h) => h.id === tool.id)}
        {#if result?.ok}
          <span class="gap-2 fr-text--sm mb-0! inline-flex items-center">
            <span class="health-dot ok" aria-hidden="true"></span>
            {m['admin.tools.list.health.ok']()}
          </span>
        {:else if result?.error}
          <span
            class="gap-2 fr-text--sm mb-0! inline-flex items-center"
            title={healthDetails[result.error]()}
          >
            <span class="health-dot error" aria-hidden="true"></span>
            {healthLabels[result.error]()}
          </span>
        {/if}
      {:catch}
        <span class="fr-text--sm mb-0! text-[--text-mention-grey]">
          {m['admin.tools.list.health.unknown']()}
        </span>
      {/await}
    {:else if col.id === 'calls'}
      <span class="font-bold">{tool.calls}</span>
      {#if tool.failures}
        <span class="fr-text--xs mb-0! block text-[--text-default-error]">
          {m['admin.tools.list.failures']({ count: tool.failures })}
        </span>
      {/if}
    {:else if col.id === 'enabled'}
      <Toggle
        id="tool-enabled-{tool.id}"
        labelPos="right"
        bind:value={() => pending[tool.id] ?? tool.enabled, (value) => setEnabled(tool, value)}
      >
        <span class="fr-sr-only">{m['admin.tools.list.switch']({ label: tool.label })}</span>
      </Toggle>
    {/if}
  {/snippet}
</Table>

<style>
  .health-dot {
    width: 0.625rem;
    height: 0.625rem;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .health-dot.ok {
    background-color: var(--success-425-625);
  }

  .health-dot.error {
    background-color: var(--error-425-625);
  }

  .health-dot.checking {
    background-color: var(--background-contrast-grey);
    animation: health-pulse 1s ease-in-out infinite alternate;
  }

  @keyframes health-pulse {
    to {
      opacity: 0.3;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .health-dot.checking {
      animation: none;
    }
  }
</style>
