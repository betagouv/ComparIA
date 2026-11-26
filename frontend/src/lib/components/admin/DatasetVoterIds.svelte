<script lang="ts">
  import { Alert, Button, Toggle } from '$components/dsfr'
  import { api, type ApiError } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { untrack } from 'svelte'

  // Whether the raw dataset carries pseudonymous voter ids, see
  // utils/dataset/voters.py. Its own section on the publishing page.
  let { enabled, onSaved }: { enabled: boolean; onSaved?: () => Promise<void> | void } = $props()

  let value = $state(untrack(() => enabled))
  let busy = $state(false)
  let error = $state<string>()

  async function save(event: SubmitEvent) {
    event.preventDefault()
    error = undefined
    busy = true
    try {
      await api.request('/admin/settings', {
        method: 'PATCH',
        body: JSON.stringify({ dataset_voter_ids: value })
      })
      useToast(m['admin.publishing.voterIds.success'](), 4000)
      await onSaved?.()
    } catch (e) {
      error = (e as ApiError).message
    } finally {
      busy = false
    }
  }
</script>

<section class="mb-10">
  <h2 class="fr-h6 mb-2!">{m['admin.publishing.voterIds.title']()}</h2>
  <p class="fr-text--sm text-grey mb-4!">{m['admin.publishing.voterIds.help']()}</p>

  <form onsubmit={save}>
    <Toggle id="dataset-voter-ids" bind:value label={m['admin.publishing.voterIds.label']()} />

    {#if value}
      <Alert
        title={m['admin.publishing.voterIds.warning']()}
        variant="warning"
        small
        class="my-4"
      />
    {/if}

    {#if error}
      <p class="fr-error-text" aria-live="polite">{error}</p>
    {/if}

    <div class="flex justify-start">
      <Button type="submit" text={m['admin.publishing.voterIds.save']()} disabled={busy} />
    </div>
  </form>
</section>
