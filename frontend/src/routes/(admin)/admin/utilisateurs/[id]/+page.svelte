<script lang="ts">
  import { goto } from '$app/navigation'
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
      url: method === 'post' ? '/admin/users' : `/admin/users/${id}`,
      ...data.formProps,
      omitKeys: ['created_at', 'last_seen_at', 'source'],
      i18nKey: 'user_upsert',
      method,
      onSuccess: () => goto(resolve('/admin/utilisateurs'))
    })
  )
</script>

<div>
  <Form {id} label="User" subLabel={data.formProps.data.email} {...form} />
</div>
