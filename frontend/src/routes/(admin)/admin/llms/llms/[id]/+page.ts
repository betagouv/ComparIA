import type { LLMData } from '$lib/generated/admin'
import { error } from '@sveltejs/kit'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ parent, params }) => {
  const { llms, schemas } = await parent()
  const data = llms.find((item) => item.id === params.id)
  if (!data && params.id !== 'create') error(404)

  return {
    formProps: { schema: schemas.llms, data: data ?? ({} as LLMData) }
  }
}
