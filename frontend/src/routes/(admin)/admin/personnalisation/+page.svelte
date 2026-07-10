<script lang="ts">
  import { Button, Input } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { api } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { onMount } from 'svelte'

  interface AppSettings {
    votes_objective: number
  }

  let loading = $state(true)
  let saving = $state(false)

  let votesObjective = $state('')

  async function load() {
    loading = true
    try {
      const data = await api.request<AppSettings>('/admin/settings')
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

<PageLayout seoTitle="Personnalisation" title="Personnalisation" subtitle="Configuration de l'application.">
  {#if loading}
    <p class="fr-text--sm text-[--text-mention-grey]">Chargement...</p>
  {:else}
    <form onsubmit={save} class="max-w-[480px]">
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
</PageLayout>
