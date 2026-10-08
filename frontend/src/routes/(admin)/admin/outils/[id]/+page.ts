import type { ToolAdmin, ToolUpsert } from '$lib/generated/admin'
import { error } from '@sveltejs/kit'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ parent, params }) => {
  const { tools, schemas } = await parent()
  const data = tools.find((item) => item.id === params.id)
  // New tools are set up step by step at /admin/outils/create.
  if (!data) error(404)

  // The form also writes the credential, which the panel is never sent.
  const formData: ToolAdmin & Pick<ToolUpsert, 'secret'> = data
  return {
    formProps: { schema: schemas.tools, data: formData }
  }
}
