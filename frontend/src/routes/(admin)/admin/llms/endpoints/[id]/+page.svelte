<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import { Button } from '$components/dsfr'
  import { FormInput, type FormInputProps } from '$components/form'
  import Form from '$components/form/Form.svelte'
  import { api } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { useForm } from '$lib/stores/form.svelte'
  import type { PageProps } from './$types'

  const { data }: PageProps = $props()

  const id = $derived(page.params.id)
  const method = $derived(id === 'create' ? 'post' : 'put')
  const hasApiKey = $derived(!!data.formProps.data.has_api_key)

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

  const apiKeyField = $derived.by(() => {
    const field = form.items.find((item) => item.id === 'api_key')!
    return (
      hasApiKey
        ? {
            ...field,
            placeholder: '• '.repeat(20),
            help: hasApiKey ? m['admin.endpointKey.hint']() : field.help
          }
        : field
    ) as FormInputProps
  })

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
  {#snippet apiKey()}
    <FormInput {...apiKeyField} type="password" bind:value={form.form['api_key']}>
      {#if hasApiKey}
        {#if confirmingRemoval}
          <Button
            id="endpoint-api-key-remove-confirm"
            variant="secondary"
            text={m['admin.endpointKey.removeConfirm']()}
            disabled={removing}
            class="text-nowrap"
            onclick={removeApiKey}
          />
          <Button
            text={m['words.back']()}
            disabled={removing}
            onclick={() => (confirmingRemoval = false)}
          />
        {:else}
          <Button
            id="endpoint-api-key-remove"
            icon="delete-bin-line"
            text={m['admin.endpointKey.remove']()}
            class="text-nowrap"
            onclick={() => (confirmingRemoval = true)}
          />
        {/if}
      {/if}
    </FormInput>
  {/snippet}

  <Form {id} label="Endpoint" subLabel={id} {...form} fieldSnippets={{ api_key: apiKey }} />
</div>
