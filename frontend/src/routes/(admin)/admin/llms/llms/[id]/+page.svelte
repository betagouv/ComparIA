<script lang="ts">
  import { page } from '$app/state'
  import Form from '$components/form/Form.svelte'
  import { omit } from '$lib/utils/commons'
  import { getFormFields } from '$lib/utils/form'
  import type { PageProps } from './$types'

  const { data: _data }: PageProps = $props()

  const omittedKeys = ['id', 'updated_at', 'created_at'] as const
  const data = $derived(_data.llms.find((item) => item.id === page.params.id)!)
  const schema = $derived.by(() => {
    const schema = _data.schemas.llms
    schema.properties!.lab_id.type = 'string'
    schema.properties!.lab_id.enum = _data.labs.map((l) => ({ label: l.name, value: l.id! }))
    schema.properties!.license_id.type = 'string'
    schema.properties!.license_id.enum = _data.licenses.map((l) => ({
      label: l.name,
      value: l.id!
    }))
    schema.properties!.endpoint_id.type = 'string'
    schema.properties!.endpoint_id.enum = _data.endpoints.map((e) => ({
      label: e.name,
      value: e.id!
    }))
    return schema
  })
  const form = $state({
    ...omit(data, omittedKeys),
    knowledge_cutoff: data.knowledge_cutoff
      ? new Date(data.knowledge_cutoff).toISOString().split('T')[0]
      : undefined,
    release_date: new Date(data.release_date).toISOString().split('T')[0]
  })
  const fields = $derived(
    getFormFields(schema, 'llm_upsert').filter((f) => !omittedKeys.includes(f.id))
  )
  let errors = $state({})
</script>

<div>
  <Form
    id={data.id}
    label="LLM"
    subLabel={data.id}
    items={fields}
    {form}
    {errors}
    url={`/admin/llms/llm/${data.id}`}
    method="put"
  />
</div>
