<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import { Badge, Button } from '$components/dsfr'
  import Form from '$components/form/Form.svelte'
  import { api } from '$lib/fastapi-client'
  import type { LLMEndpointPublic } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { useForm } from '$lib/stores/form.svelte'
  import type { PageProps } from './$types'

  const { data }: PageProps = $props()

  const id = $derived(page.params.id)
  const method = $derived(id === 'create' ? 'post' : 'put')
  const hasApiKey = $derived(!!(data.formProps.data as LLMEndpointPublic).has_api_key)

  let confirmingRemoval = $state(false)
  let removing = $state(false)

  const form = $derived(
    useForm({
      url: '/admin/llms/endpoint',
      ...data.formProps,
      omitKeys: ['updated_at', 'created_at'],
      i18nKey: 'endpoint_upsert',
      method,
      onSuccess: (updated) => {
        Object.assign(data.formProps.data, updated)
        if (method === 'post') {
          // Update app data
          data.endpoints.push(updated)
          goto(resolve(`/admin/llms/endpoints/${updated.id}`))
        }
      }
    })
  )

  async function removeApiKey() {
    removing = true
    try {
      await api.request(`/admin/llms/endpoint/${id}/api-key`, { method: 'delete' })
      confirmingRemoval = false
      await invalidateAll()
      useToast(m['admin.endpointKey.removed'](), 5000, 'success')
    } catch (error) {
      useToast((error as Error).message, 6000, 'error')
    } finally {
      removing = false
    }
  }
</script>

<div>
  <Form {id} label="Endpoint" subLabel={id} {...form} />

  {#if id !== 'create'}
    <div id="endpoint-api-key-state" class="gap-3 mt-6 flex flex-wrap items-center">
      <Badge
        size="sm"
        variant={hasApiKey ? 'green' : 'orange'}
        text={hasApiKey ? m['admin.endpointKey.set']() : m['admin.endpointKey.unset']()}
      />
      <span class="fr-text--sm text-[--text-mention-grey]">
        {m['admin.endpointKey.hint']()}
      </span>

      {#if hasApiKey}
        {#if confirmingRemoval}
          <Button
            id="endpoint-api-key-remove-confirm"
            variant="secondary"
            text={m['admin.endpointKey.removeConfirm']()}
            disabled={removing}
            onclick={removeApiKey}
          />
          <Button
            variant="tertiary-no-outline"
            text={m['words.back']()}
            disabled={removing}
            onclick={() => (confirmingRemoval = false)}
          />
        {:else}
          <Button
            id="endpoint-api-key-remove"
            variant="tertiary-no-outline"
            text={m['admin.endpointKey.remove']()}
            onclick={() => (confirmingRemoval = true)}
          />
        {/if}
      {/if}
    </div>
  {/if}
</div>
