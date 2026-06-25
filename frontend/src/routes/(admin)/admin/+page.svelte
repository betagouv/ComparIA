<script lang="ts">
  import { Badge, Button, Table } from '$components/dsfr'
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
  let search = $state<string>('')

  async function fetchUsers() {
    loading = true
    try {
      const params = new URLSearchParams({ page: '1', page_size: '50' })
      if (search) params.set('search', search)
      const data = await api.request<{ items: UserRow[]; total: number }>(
        `/admin/users?${params}`,
        { credentials: 'include' }
      )
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
    { id: 'actions', label: 'Actions' },
  ]

  const tableRows = $derived(users.map((u) => ({ ...u })))

  // Auth settings stubs
  let accessMode = $state<'none' | 'optional' | 'required'>('optional')
  let emailOtpEnabled = $state(false)
  let oidcEnabled = $state(false)
</script>

<div class="px-8 py-8">
  <div class="mb-6 flex items-baseline justify-between">
    <h1 class="text-2xl font-bold">Users</h1>
    <span class="text-sm text-gray-400">Authentication mode and registered users</span>
  </div>

  <div class="gap-8 grid grid-cols-[400px_1fr]">
    <!-- Auth settings (stub) -->
    <section>
      <h2 class="mb-4 text-xs font-semibold uppercase tracking-wider text-gray-400">
        Authentication settings
      </h2>

      <div class="mb-6">
        <p class="mb-2 text-sm font-medium">Access mode</p>

        {#each [
          { value: 'none', label: 'No authentication', desc: 'Anonymous usage only. Matches the current public default.' },
          { value: 'optional', label: 'Anonymous + sign-in', desc: 'Anyone can browse; signing in unlocks saved history and verified-pro features.' },
          { value: 'required', label: 'Sign-in required', desc: 'No anonymous access. Default mode for sector-restricted deployments (e.g. Compar:IA Santé).' },
        ] as opt}
          <label class="mb-3 flex cursor-not-allowed gap-3 opacity-60">
            <input
              type="radio"
              name="access_mode"
              value={opt.value}
              bind:group={accessMode}
              disabled
              class="mt-0.5 shrink-0"
            />
            <div>
              <span class="text-sm font-medium">{opt.label}</span>
              <p class="m-0 text-xs text-gray-500">{opt.desc}</p>
            </div>
          </label>
        {/each}
      </div>

      <div class="rounded-lg border border-gray-200 bg-white p-4">
        <label class="mb-2 flex cursor-not-allowed items-center gap-2 opacity-60">
          <input type="checkbox" bind:checked={emailOtpEnabled} disabled />
          <span class="text-sm font-medium">One-time code (email)</span>
        </label>
        <p class="mb-2 ml-5 text-xs text-gray-400">SMTP credentials must be set in environment variables.</p>
        <Badge variant="orange" size="sm" text="SMTP not configured in env" class="ml-5" />

        <hr class="my-4 border-gray-100" />

        <label class="mb-4 flex cursor-not-allowed items-center gap-2 opacity-60">
          <input type="checkbox" bind:checked={oidcEnabled} disabled />
          <span class="text-sm font-medium">OIDC single sign-on</span>
        </label>
        <p class="ml-5 text-xs text-gray-400">Identity provider via discovery URL.</p>
      </div>

      <div class="mt-4 flex gap-2">
        <Button text="Save changes" disabled />
        <Button text="Discard" variant="secondary" disabled />
      </div>
    </section>

    <!-- User management -->
    <section>
      <h2 class="mb-4 text-xs font-semibold uppercase tracking-wider text-gray-400">
        User management
      </h2>

      <Table
        caption="Users"
        hideCaption
        {cols}
        rows={tableRows}
        bind:search
      >
        {#snippet headerRight()}
          <Button text="Invite user" disabled />
        {/snippet}

        {#snippet cell(row, col)}
          {#if col.id === 'email'}
            <span class="text-sm">{row.email}</span>
          {:else if col.id === 'source'}
            <Badge size="sm" text={row.source} variant="light-info" />
          {:else if col.id === 'created_at'}
            <span class="text-sm text-gray-500">{relativeTime(row.created_at)}</span>
          {:else if col.id === 'actions'}
            <span class="text-sm text-gray-300">—</span>
          {/if}
        {/snippet}
      </Table>

      {#if !loading}
        <p class="mt-2 text-xs text-gray-400">
          {total} user{total !== 1 ? 's' : ''}.
          New users are created on first SSO login or via invite.
        </p>
      {/if}
    </section>
  </div>
</div>
