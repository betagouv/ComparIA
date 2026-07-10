<script lang="ts">
  import { Button, Input, Select } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { api } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { onMount } from 'svelte'

  interface AppSettings {
    auth_access_policy: 'anonymous_first' | 'sign_in_required'
    auth_domain_allowlist: string[]
  }

  let loading = $state(true)
  let saving = $state(false)

  let accessPolicy = $state<'anonymous_first' | 'sign_in_required'>('anonymous_first')
  let domainAllowlist = $state('')

  async function load() {
    loading = true
    try {
      const data = await api.request<AppSettings>('/admin/settings')
      accessPolicy = data.auth_access_policy
      domainAllowlist = data.auth_domain_allowlist.join(', ')
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
            .filter(Boolean)
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

<PageLayout seoTitle="Authentification" title="Authentification" subtitle="Configuration de l'application.">
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
      <Button type="submit" text={saving ? 'Enregistrement...' : 'Enregistrer'} disabled={saving} class="mt-4!" />
    </form>
  {/if}
</PageLayout>
