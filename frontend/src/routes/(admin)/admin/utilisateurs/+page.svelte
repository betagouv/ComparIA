<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { Badge, Button, Icon, Link, Table } from '$components/dsfr'
  import ConfirmDeleteUserModal from '$components/ConfirmDeleteUserModal.svelte'
  import InviteUserModal from '$components/InviteUserModal.svelte'
  import PageLayout from '$components/PageLayout.svelte'
  import { getAuthContext } from '$lib/auth.svelte'
  import { api } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { getLocale } from '$lib/i18n/runtime'
  import type { OrderingMethod, TableCol } from '$lib/utils/data'
  import { sortRows, toRelativeTime, toSearchString } from '$lib/utils/data'
  import type { PageProps } from './$types'

  const { data }: PageProps = $props()
  const refetch = () => invalidate('admin:users')
  const locale = getLocale()
  const auth = getAuthContext()

  const users = $derived(data.users.items)
  const total = $derived(data.users.total)

  function sourceBadgeVariant(source: string) {
    switch (source) {
      case 'email_code':
        return 'info'
      case 'email_invitation':
        return 'green'
      case 'pending_invite':
        return 'yellow'
      case 'added_manually':
        return 'purple'
      default:
        return ''
    }
  }

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
      await refetch()
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    }
  }

  async function cancelInvite(row: { id: string; email: string }) {
    try {
      await api.request(`/admin/users/${row.id}/invite`, { method: 'DELETE' })
      useToast(`Invite for ${row.email} canceled, user removed`, 4000)
      await refetch()
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
      id: u.id!,
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
      <div class="gap-2 flex">
        <Link
          button
          variant="secondary"
          text="Add user"
          href={resolve('/admin/utilisateurs/create')}
        />
        <Button text="Invite user" aria-controls="fr-modal-invite-user" data-fr-opened="false" />
      </div>
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
            <Link
              button
              iconOnly
              variant="tertiary-no-outline"
              size="sm"
              title="Edit user"
              aria-label={`Edit ${row.email}`}
              href={resolve(`/admin/utilisateurs/${row.id}`)}
            >
              <Icon icon="i-ri-edit-line" />
            </Link>
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

  <p class="fr-text--sm mt-2! text-[--text-mention-grey]">
    {total} user{total !== 1 ? 's' : ''}.
  </p>
</PageLayout>

<InviteUserModal onSuccess={refetch} />
<ConfirmDeleteUserModal email={userToDelete?.email ?? null} onConfirm={confirmDelete} />
