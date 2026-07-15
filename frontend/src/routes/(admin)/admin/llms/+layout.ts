import { api } from '$lib/fastapi-client'
import type { LLMData, LLMEndpoint, LLMLab, LLMLicense } from '$lib/generated/admin'
import type { JSONSchema } from '$lib/utils/form'
import type { LayoutLoad } from './$types'

export const ssr = false // auth error on server side

export const load: LayoutLoad = async () => {
  const data = await api.request<{
    endpoints: LLMEndpoint[]
    licenses: LLMLicense[]
    labs: LLMLab[]
    llms: LLMData[]
  }>('/admin/llms/data')
  const schemas = await api.request<{
    endpoints: JSONSchema
    licenses: JSONSchema
    labs: JSONSchema
    llms: JSONSchema
  }>('/admin/llms/schemas')

  const llmsSchemaProps = schemas.llms.properties!

  llmsSchemaProps.lab_id.type = 'string'
  llmsSchemaProps.lab_id.enum = data.labs.map((l) => ({ label: l.name, value: l.id! }))
  llmsSchemaProps.license_id.type = 'string'
  llmsSchemaProps.license_id.enum = data.licenses.map((l) => ({
    label: l.name,
    value: l.id!
  }))
  llmsSchemaProps.endpoint_id.type = 'string'
  llmsSchemaProps.endpoint_id.enum = data.endpoints.map((e) => ({
    label: e.name,
    value: e.id!
  }))

  return {
    ...data,
    schemas
  }
}
