import type { LLMEndpointPublic } from '$lib/generated/admin'
import { error } from '@sveltejs/kit'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ parent, params }) => {
  const { endpoints, schemas } = await parent()
  const data = endpoints.find((item) => item.id === params.id)
  if (!data && params.id !== 'create') error(404)

  return {
    formProps: { schema: schemas.endpoints, data: data ?? ({} as LLMEndpointPublic) }
  }
}
