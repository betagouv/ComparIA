<script lang="ts">
  import { Badge, Button, Icon, Table } from '$components/dsfr'
  import ConfirmDeleteUserModal from '$components/ConfirmDeleteUserModal.svelte'
  import ConfirmPromoteAdminModal from '$components/ConfirmPromoteAdminModal.svelte'
  import InviteUserModal from '$components/InviteUserModal.svelte'
  import PageLayout from '$components/PageLayout.svelte'
  import { auth } from '$lib/auth.svelte'
  import { api } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { getLocale } from '$lib/i18n/runtime'
  import type { OrderingMethod, TableCol } from '$lib/utils/data'
  import { sortRows, toRelativeTime, toSearchString } from '$lib/utils/data'
  import { onMount } from 'svelte'

  const locale = getLocale()

  interface UserRow {
    id: string
    email: string
    role: string
    source: string
    created_at: string
    last_seen_at: string
  }

  function sourceBadgeVariant(source: string) {
    switch (source) {
      case 'email_code':
        return 'info'
      case 'email_invitation':
        return 'green'
      case 'pending_invite':
        return 'yellow'
      default:
        return ''
    }
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

  let userToDelete = $state<{ id: string; email: string } | null>(null)

  function openDeleteModal(row: { id: string; email: string }) {
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

  let userToPromote = $state<{ id: string; email: string } | null>(null)

  function openPromoteModal(row: { id: string; email: string }) {
    userToPromote = row
    const el = document.getElementById('fr-modal-promote-admin')
    if (el) {
      // @ts-expect-error - DSFR is globally available
      window.dsfr(el).modal.disclose()
    }
  }

  async function confirmPromote() {
    if (!userToPromote) return
    try {
      await api.request(`/admin/users/${userToPromote.id}/role`, {
        method: 'PATCH',
        body: JSON.stringify({ role: 'admin' })
      })
      useToast(`${userToPromote.email} promoted to admin`, 4000)
      await fetchUsers()
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    }
  }

  async function cancelInvite(row: { id: string; email: string }) {
    try {
      await api.request(`/admin/users/${row.id}/invite`, { method: 'DELETE' })
      useToast(`Invite for ${row.email} canceled, user removed`, 4000)
      await fetchUsers()
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    }
  }

  const cols = [
    { id: 'email', label: 'Email', orderable: true },
    { id: 'source', label: 'Source', orderable: true },
    { id: 'created_at', label: 'Added', kind: 'date', orderable: true },
    { id: 'actions', label: 'Actions' }
  ] satisfies TableCol[]
  type ColKey = (typeof cols)[number]['id']

  let orderingCol = $state<ColKey>('created_at')
  let orderingMethod = $state<OrderingMethod>('descending')
  let search = $state('')

  const tableRows = $derived(
    users.map((u) => ({
      ...u,
      created_at: new Date(u.created_at),
      search: toSearchString([u.email, u.source]),
      actions: undefined
    }))
  )
  const sortedRows = $derived(
    sortRows(tableRows, cols, { col: orderingCol, method: orderingMethod, search })
  )
</script>

<PageLayout seoTitle="Users" title="Users" subtitle="Registered users">
  <Table
    bind:search
    bind:orderingMethod
    bind:orderingCol
    caption="Users"
    hideCaption
    {cols}
    rows={sortedRows}
  >
    {#snippet headerRight()}
      <Button text="Invite user" aria-controls="fr-modal-invite-user" data-fr-opened="false" />
    {/snippet}

    {#snippet cell(row, col)}
      {#if col.id === 'email'}
        <span class="fr-text--sm">{row.email}</span>
      {:else if col.id === 'source'}
        <Badge size="sm" text={row.source} variant={sourceBadgeVariant(row.source)} />
      {:else if col.id === 'created_at'}
        <span class="fr-text--sm text-[--text-mention-grey]">
          {toRelativeTime(row.created_at, locale)}
        </span>
      {:else if col.id === 'actions'}
        {#if row.email === auth.user?.email}
          <span class="fr-text--sm text-[--text-disabled-grey]">—</span>
        {:else}
          <div class="gap-1 flex items-center justify-end">
            {#if row.source === 'pending_invite'}
              <Button
                iconOnly
                variant="tertiary-no-outline"
                size="sm"
                title="Cancel invite"
                aria-label={`Cancel invite for ${row.email}`}
                onclick={() => cancelInvite(row)}
              >
                <Icon icon="i-ri-mail-close-line" />
              </Button>
            {/if}
            {#if row.role !== 'admin'}
              <Button
                iconOnly
                variant="tertiary-no-outline"
                size="sm"
                title="Promote to admin"
                aria-label={`Promote ${row.email} to admin`}
                onclick={() => openPromoteModal(row)}
              >
                <Icon icon="i-ri-shield-star-line" />
              </Button>
            {/if}
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
          </div>
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
<ConfirmPromoteAdminModal email={userToPromote?.email ?? null} onConfirm={confirmPromote} />
