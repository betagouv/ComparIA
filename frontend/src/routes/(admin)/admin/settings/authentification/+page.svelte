<script lang="ts">
  import { Button, Input, Select } from '$components/dsfr'
  import { api } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { onMount } from 'svelte'

  interface AppSettings {
    auth_access_policy: 'anonymous_first' | 'sign_in_required'
    auth_domain_allowlist: string[]
    votes_objective: number
  }

  let loading = $state(true)
  let saving = $state(false)

  let accessPolicy = $state<'anonymous_first' | 'sign_in_required'>('anonymous_first')
  let domainAllowlist = $state('')
  let votesObjective = $state('')

  async function load() {
    loading = true
    try {
      const data = await api.request<AppSettings>('/admin/settings')
      accessPolicy = data.auth_access_policy
      domainAllowlist = data.auth_domain_allowlist.join(', ')
      votesObjective = String(data.votes_objective)
    } finally {
      loading = false
    }
  }

  onMount(load)

  async function save(e: SubmitEvent) {
    e.preventDefault()
    saving = true
    try {
      await api.request('/admin/settings', {
        method: 'PATCH',
        body: JSON.stringify({
          auth_access_policy: accessPolicy,
          auth_domain_allowlist: domainAllowlist
            .split(',')
            .map((domain) => domain.trim())
            .filter(Boolean),
          votes_objective: Number(votesObjective)
        })
      })
      useToast('Paramètres mis à jour', 4000)
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      saving = false
    }
  }
</script>

{#if loading}
  <p class="fr-text--sm text-[--text-mention-grey]">Chargement...</p>
{:else}
  <form onsubmit={save} class="max-w-[480px]">
    <Select
      id="settings-access-policy"
      label="Mode d'accès"
      bind:selected={accessPolicy}
      options={[
        { value: 'anonymous_first', label: 'Connexion facultative (anonymous_first)' },
        { value: 'sign_in_required', label: 'Connexion obligatoire (sign_in_required)' }
      ]}
    />
    <Input
      id="settings-domain-allowlist"
      label="Domaines autorisés"
      help="Séparés par des virgules. Laisser vide pour autoriser tous les domaines."
      bind:value={domainAllowlist}
      groupClass="mt-4!"
    />
    <Input
      id="settings-votes-objective"
      type="number"
      min="0"
      label="Objectif de votes"
      bind:value={votesObjective}
      groupClass="mt-4!"
    />
    <Button type="submit" text={saving ? 'Enregistrement...' : 'Enregistrer'} disabled={saving} class="mt-4!" />
  </form>
{/if}
