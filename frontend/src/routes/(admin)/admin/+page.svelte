<script lang="ts">
  import { Badge, Button, Table } from '$components/dsfr'
  import Icon from '$components/dsfr/Icon.svelte'
  import ConfirmDeleteUserModal from '$components/ConfirmDeleteUserModal.svelte'
  import InviteUserModal from '$components/InviteUserModal.svelte'
  import PageLayout from '$components/PageLayout.svelte'
  import { auth } from '$lib/auth.svelte'
  import { api } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
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

  let userToDelete = $state<UserRow | null>(null)

  function openDeleteModal(row: UserRow) {
    userToDelete = row
    const el = document.getElementById('fr-modal-delete-user')
    if (el) {
      // @ts-expect-error - DSFR is globally available
      window.dsfr(el).modal.disclose()
    }
  }

  async function confirmDelete() {
    if (!userToDelete) return
    try {
      await api.request(`/admin/users/${userToDelete.id}`, { method: 'DELETE' })
      useToast(`${userToDelete.email} deleted`, 4000)
      await fetchUsers()
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    }
  }

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
      <Button text="Invite user" aria-controls="fr-modal-invite-user" data-fr-opened="false" />
    {/snippet}

    {#snippet cell(row, col)}
      {#if col.id === 'email'}
        <span class="fr-text--sm">{row.email}</span>
      {:else if col.id === 'source'}
        <Badge size="sm" text={row.source} variant="light-info" />
      {:else if col.id === 'created_at'}
        <span class="fr-text--sm text-[--text-mention-grey]">{relativeTime(row.created_at)}</span>
      {:else if col.id === 'actions'}
        {#if row.email === auth.user?.email}
          <span class="fr-text--sm text-[--text-disabled-grey]">—</span>
        {:else}
          <Button
            iconOnly
            variant="tertiary-no-outline"
            size="sm"
            title="Delete user"
            aria-label={`Delete ${row.email}`}
            class="text-[--text-default-error]!"
            onclick={() => openDeleteModal(row)}
          >
            <Icon icon="i-ri-delete-bin-line" />
          </Button>
        {/if}
      {/if}
    {/snippet}
  </Table>

  {#if !loading}
    <p class="fr-text--sm mt-2! text-[--text-mention-grey]">
      {total} user{total !== 1 ? 's' : ''}.
    </p>
  {/if}
</PageLayout>

<InviteUserModal onSuccess={fetchUsers} />
<ConfirmDeleteUserModal email={userToDelete?.email ?? null} onConfirm={confirmDelete} />
