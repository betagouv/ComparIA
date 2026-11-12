<script lang="ts">
  import { goto, invalidate } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import Form from '$components/form/Form.svelte'
  import { useFormSchema } from '$lib/stores/form.svelte'
  import type { PageProps } from './$types'

  const { data }: PageProps = $props()

  const id = $derived(page.params.id)
  const method = $derived(id === 'create' ? 'post' : 'put')
  const form = $derived(
    useFormSchema({
      url: '/admin/llms/llm',
      initialData: () => data.formProps.data,
      schema: () => data.formProps.schema,
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

  // Tags already in use, offered while typing so 'legal' is not typed twice
  // as 'legal' and 'juridique'.
  const tagSuggestions = $derived([...new Set(data.llms.flatMap((llm) => llm.tags ?? []))].sort())
  const items = $derived(
    form.items.map((item) => (item.id === 'tags' ? { ...item, suggestions: tagSuggestions } : item))
  )
</script>

<div>
  <Form
    {id}
    label="LLM"
    subLabel={id}
    {...form}
    {items}
    class="mt-6! p-6 cg-border max-w-[700px]"
  />
</div>
