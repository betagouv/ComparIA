<script lang="ts">
  import { goto, invalidate, invalidateAll } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import { FormSecretInput, type FormInputProps } from '$components/form'
  import Form from '$components/form/Form.svelte'
  import { m } from '$lib/i18n/messages'
  import { useForm } from '$lib/stores/form.svelte'
  import type { PageProps } from './$types'

  const { data }: PageProps = $props()

  const id = $derived(page.params.id)
  const method = $derived(id === 'create' ? 'post' : 'put')
  const hasApiKey = $derived(!!data.formProps.data.has_api_key)

  const form = $derived(
    useForm({
      url: '/admin/llms/endpoint',
      ...data.formProps,
      omitKeys: ['updated_at', 'created_at'],
      i18nKey: 'endpoint_upsert',
      method,
      onSuccess: async (updated) => {
        await invalidate('admin:llms')
        if (method === 'post') {
          await goto(resolve(`/admin/llms/endpoints/${updated.id}`))
        }
      }
    })
  )

  const apiKeyField = $derived(form.items.find((item) => item.id === 'api_key') as FormInputProps)
</script>

<div>
  {#snippet apiKey()}
    <FormSecretInput
      {...apiKeyField}
      stored={hasApiKey}
      removeUrl="/admin/llms/endpoint/{id}/api-key"
      removedMessage={m['admin.endpointKey.removed']()}
      removeId="endpoint-api-key-remove"
      onremoved={invalidateAll}
      bind:value={form.form['api_key']}
    />
  {/snippet}

  <Form {id} label="Endpoint" subLabel={id} {...form} fieldSnippets={{ api_key: apiKey }} />
</div>
