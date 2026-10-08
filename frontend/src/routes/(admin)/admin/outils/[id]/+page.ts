import type { ToolAdmin, ToolUpsert } from '$lib/generated/admin'
import { error } from '@sveltejs/kit'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ parent, params }) => {
  const { tools, schemas } = await parent()
  const data = tools.find((item) => item.id === params.id)
  if (!data && params.id !== 'create') error(404)

  // The form also writes the credential, which the panel is never sent.
  const formData: ToolAdmin & Pick<ToolUpsert, 'secret'> = data ?? ({} as ToolAdmin)
  return {
    formProps: { schema: schemas.tools, data: formData }
  }
}
