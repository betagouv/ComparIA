import { api } from '$lib/fastapi-client'
import type { UserPublic } from '$lib/generated/admin'
import type { JSONSchema } from '$lib/utils/form'
import type { PageLoad } from './$types'

export const ssr = false // auth error on server side

export const load: PageLoad = async ({ params }) => {
  const schema = await api.request<JSONSchema>('/admin/users/schema')

  if (params.id === 'create') {
    return {
      formProps: { schema, data: { role: 'user' } as UserPublic }
    }
  }

  // Email is only editable when creating a user, not when editing one.
  schema.properties!.email.disabled = true
  schema.properties!.email.hidden = true

  const data = await api.request<UserPublic>(`/admin/users/${params.id}`)

  return {
    formProps: { schema, data }
  }
}
