<script lang="ts">
  import { Badge, Button, Table } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { api } from '$lib/fastapi-client'
  import { onMount } from 'svelte'

  interface UserRow {
    id: string
    email: string
    role: string
    source: string
    created_at: string
    last_seen_at: string
  }

  let users = $state<UserRow[]>([])
  let total = $state(0)
  let loading = $state(true)

  async function fetchUsers() {
    loading = true
    try {
      const params = new URLSearchParams({ page: '1', page_size: '50' })
      const data = await api.request<{ items: UserRow[]; total: number }>(`/admin/users?${params}`)
      users = data.items
      total = data.total
    } finally {
      loading = false
    }
  }

  onMount(fetchUsers)

  function relativeTime(iso: string): string {
    const diff = Date.now() - new Date(iso).getTime()
    const days = Math.floor(diff / 86400000)
    if (days === 0) return 'today'
    if (days === 1) return '1 day ago'
    if (days < 30) return `${days} days ago`
    const months = Math.floor(days / 30)
    if (months === 1) return '1 month ago'
    return `${months} months ago`
  }

  const cols = [
    { id: 'email', label: 'Email' },
    { id: 'source', label: 'Source' },
    { id: 'created_at', label: 'Added' },
    { id: 'actions', label: 'Actions' }
  ]

  const tableRows = $derived(users.map((u) => ({ ...u })))
</script>

<PageLayout seoTitle="Users" title="Users" subtitle="Registered users">
  <Table caption="Users" hideCaption {cols} rows={tableRows}>
    {#snippet headerRight()}
      <Button text="Invite user" disabled />
    {/snippet}

    {#snippet cell(row, col)}
      {#if col.id === 'email'}
        <span class="fr-text--sm">{row.email}</span>
      {:else if col.id === 'source'}
        <Badge size="sm" text={row.source} variant="light-info" />
      {:else if col.id === 'created_at'}
        <span class="fr-text--sm text-[--text-mention-grey]">{relativeTime(row.created_at)}</span>
      {:else if col.id === 'actions'}
        <span class="fr-text--sm text-[--text-disabled-grey]">—</span>
      {/if}
    {/snippet}
  </Table>

  {#if !loading}
    <p class="fr-text--sm mt-2! text-[--text-mention-grey]">
      {total} user{total !== 1 ? 's' : ''}.
    </p>
  {/if}
</PageLayout>
