import type { LLMLabPublic } from '$lib/generated/admin'
import { error } from '@sveltejs/kit'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ parent, params }) => {
  const { labs, schemas } = await parent()
  const data = labs.find((item) => item.id === params.id)
  if (!data && params.id !== 'create') error(404)

  return {
    formProps: { schema: schemas.labs, data: data ?? ({} as LLMLabPublic) }
  }
}
