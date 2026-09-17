import type { LLMLicense } from '$lib/generated/admin'
import { error } from '@sveltejs/kit'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ parent, params }) => {
  const { licenses, schemas } = await parent()
  const data = licenses.find((item) => item.id === params.id)
  if (!data && params.id !== 'create') error(404)

  return {
    formProps: { schema: schemas.licenses, data: data ?? ({} as LLMLicense) }
  }
}
