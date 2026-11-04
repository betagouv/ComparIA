<script lang="ts">
  import { goto } from '$app/navigation'
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
      url: method === 'post' ? '/admin/users' : `/admin/users/${id}`,
      initialData: () => data.formProps.data,
      schema: () => data.formProps.schema,
      omitKeys: ['created_at', 'last_seen_at', 'source'],
      i18nKey: 'user_upsert',
      method,
      onSuccess: () => goto(resolve('/admin/utilisateurs'))
    })
  )
</script>

<div>
  <Form
    {id}
    label="User"
    subLabel={data.formProps.data.email}
    {...form}
    class="mt-6! p-6 cg-border max-w-[700px]"
  />
</div>
