import { api } from '$lib/fastapi-client'
import type {
  LLMData,
  LLMLabPublic,
  LLMLicense,
  SelectionModeAdmin,
  ToolAdmin
} from '$lib/generated/admin'
import type { JSONSchema } from '$lib/utils/form'
import type { LayoutLoad } from './$types'
import { MODE_CHOICES } from './mode'

export const load: LayoutLoad = async ({ fetch, depends }) => {
  depends('admin:selection-modes')
  const [modes, schemas, catalog, tools] = await Promise.all([
    api.request<SelectionModeAdmin[]>('/admin/selection-modes', { fetch }),
    api.request<{ selection_mode: JSONSchema }>('/admin/selection-modes/schemas', { fetch }),
    api.request<{ llms: LLMData[]; labs: LLMLabPublic[]; licenses: LLMLicense[] }>(
      '/admin/llms/data',
      { fetch }
    ),
    api.request<{ tools: ToolAdmin[] }>('/admin/tools/data', { fetch })
  ])

  const schemaProps = schemas.selection_mode.properties!
  for (const [field, choices] of Object.entries(MODE_CHOICES)) {
    schemaProps[field].radio = true
    schemaProps[field].enum = choices().map((choice) => ({ ...choice }))
  }

  return {
    modes,
    schema: schemas.selection_mode,
    llms: catalog.llms,
    labs: catalog.labs,
    licenses: catalog.licenses,
    tools: tools.tools
  }
}
