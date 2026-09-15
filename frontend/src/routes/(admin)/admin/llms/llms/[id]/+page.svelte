<script lang="ts">
  import { goto, invalidate } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import Form from '$components/form/Form.svelte'
  import { useForm } from '$lib/stores/form.svelte'
  import type { PageProps } from './$types'

  const { data }: PageProps = $props()

  const id = $derived(page.params.id)
  const method = $derived(id === 'create' ? 'post' : 'put')
  const form = $derived(
    useForm({
      url: '/admin/llms/llm',
      ...data.formProps,
      omitKeys: ['updated_at', 'created_at'],
      i18nKey: 'llm_upsert',
      method,
      onSuccess: async (updated) => {
        await invalidate('admin:llms')
        if (method === 'post') {
          await goto(resolve(`/admin/llms/llms/${updated.id}`))
        }
      }
    })
  )
</script>

<div>
  <Form {id} label="LLM" subLabel={id} {...form} />
</div>
