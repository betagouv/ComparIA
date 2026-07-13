<script lang="ts">
  import { page } from '$app/state'
  import Form from '$components/form/Form.svelte'
  import { omit } from '$lib/utils/commons'
  import { getFormFields } from '$lib/utils/form'
  import type { PageProps } from './$types'

  const { data: _data }: PageProps = $props()

  const omittedKeys = ['id', 'updated_at', 'created_at'] as const
  const data = $derived(_data.licenses.find((item) => item.id === page.params.id)!)
  const schema = $derived(_data.schemas.licenses)
  const form = $state({ ...omit(data, omittedKeys) })
  const fields = $derived(
    getFormFields(schema, 'license_upsert').filter((f) => !omittedKeys.includes(f.id))
  )
  let errors = $state({})
</script>

<div>
  <Form
    id={data.id}
    label="License"
    subLabel={data.id}
    items={fields}
    {form}
    {errors}
    url={`/admin/llms/license/${data.id}`}
    method="put"
  />
</div>
