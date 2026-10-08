<script lang="ts">
  import { invalidateAll } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { Table, Toggle } from '$components/dsfr'
  import Link from '$components/dsfr/Link.svelte'
  import { api } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import type { OrderingMethod, TableCol } from '$lib/utils/data'
  import { sortRows, toRelativeTime, toSearchString } from '$lib/utils/data'

  import type { PageProps } from './$types'

  let { data }: PageProps = $props()
  const locale = getLocale()
  const baseRoute = '/admin/outils' as const

  const tools = $derived(
    data.tools.map((tool) => ({
      ...tool,
      address: tool.kind === 'mcp' ? (tool.url ?? '') : m['admin.tools.list.builtin'](),
      functions: tool.allowed_functions?.length ?? 0,
      enabled: tool.enabled ?? false,
      has_secret: tool.has_secret ?? false,
      updated_at: new Date(tool.updated_at!),
      created_at: new Date(tool.created_at!),
      id: tool.id!,
      search: toSearchString([tool.label, tool.key, tool.url ?? '', tool.description ?? ''])
    }))
  )
  type DataKey = keyof (typeof tools)[number]
  const cols = [
    { id: 'label', label: m['admin.tools.list.label'](), orderable: true },
    { id: 'enabled', label: m['admin.tools.list.enabled'](), orderable: true },
    { id: 'address', label: m['admin.tools.list.address'](), orderable: true },
    { id: 'functions', label: m['admin.tools.list.functions'](), orderable: true },
    { id: 'has_secret', label: m['admin.tools.list.secret'](), orderable: true },
    { id: 'updated_at', label: m['admin.tools.list.updated'](), kind: 'date', orderable: true }
  ] satisfies TableCol<DataKey>[]
  type ColKey = (typeof cols)[number]['id']

  let orderingCol = $state<ColKey>('label')
  let orderingMethod = $state<OrderingMethod>('descending')
  let search = $state('')

  const sortedRows = $derived(
    sortRows(tools, cols, { col: orderingCol, method: orderingMethod, search })
  )

  // What the switch shows while its request is out, so it moves on click.
  let pending = $state<Record<string, boolean>>({})

  async function setEnabled(tool: { id: string; label: string }, enabled: boolean) {
    pending[tool.id] = enabled
    try {
      await api.request(`/admin/tools/tool/${tool.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ enabled })
      })
      await invalidateAll()
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
    <Link
      button
      icon="add-line"
      text={m['admin.tools.list.add']()}
      href={resolve(`${baseRoute}/create`)}
    />
  {/snippet}

  {#snippet cell(tool, col)}
    {#if col.id === 'label'}
      <a href={resolve(`${baseRoute}/${tool.id}`)} class="font-bold">{tool.label}</a>
      {#if tool.description}
        <span class="fr-text--xs mb-0! block text-[--text-mention-grey]">{tool.description}</span>
      {/if}
    {:else if col.id === 'address'}
      <span class="fr-text--sm break-all">{tool.address}</span>
    {:else if col.id === 'functions'}
      {#if tool.kind !== 'mcp'}
        <span class="text-[--text-mention-grey]">-</span>
      {:else if tool.functions}
        {m['admin.tools.list.someFunctions']({ count: tool.functions })}
      {:else}
        {m['admin.tools.list.allFunctions']()}
      {/if}
    {:else if col.id === 'has_secret'}
      {tool.has_secret ? m['admin.tools.secretSet']() : m['admin.tools.secretUnset']()}
    {:else if col.id === 'enabled'}
      <Toggle
        id="tool-enabled-{tool.id}"
        labelPos="right"
        bind:value={() => pending[tool.id] ?? tool.enabled, (value) => setEnabled(tool, value)}
      >
        <span class="fr-sr-only">{m['admin.tools.list.switch']({ label: tool.label })}</span>
      </Toggle>
    {:else if col.id === 'updated_at'}
      <span class="fr-text--sm text-[--text-mention-grey]">
        {toRelativeTime(tool[col.id], locale)}
      </span>
    {/if}
  {/snippet}
</Table>
