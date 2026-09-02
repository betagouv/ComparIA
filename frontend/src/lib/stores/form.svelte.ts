import { api, ValidationError } from '$lib/fastapi-client'
import { useToast } from '$lib/helpers/useToast.svelte'
import { getKeys, omit } from '$lib/utils/commons'
import { getFormFields, type JSONSchema } from '$lib/utils/form'

type UseFormOptions<T, K> = {
  url: string
  data: T
  schema: JSONSchema
  i18nKey: string
  omitKeys?: K[]
  method?: 'post' | 'put'
  onSuccess?: (data: T) => void
  onMutateForm?: (data: T) => T
}
export function useForm<T extends Record<PropertyKey, any>, K extends keyof T>({
  url,
  data,
  schema,
  i18nKey,
  omitKeys,
  method,
  onSuccess,
  onMutateForm
}: UseFormOptions<T, K>) {
  const errors = $state<Record<string, string>>({})
  const form = $state<Partial<T>>({})
  const items = $derived(
    getFormFields(schema, i18nKey).filter((f) => !omitKeys?.includes(f.id as K))
  )
  mutateForm(data)

  function mutateForm(data: T) {
    const updated = onMutateForm?.(data) ?? data
    Object.assign(form, { ...omit(updated, omitKeys ?? []) })
  }

  async function onSubmit() {
    getKeys(errors).forEach((k) => delete errors[k])

    try {
      const updated = await api.request<T>(url, { body: JSON.stringify(form), method })
      // FIXME i18n
      useToast('Successfully saved data', 5000, 'success')
      // Mutate local form
      mutateForm(updated)
      onSuccess?.(updated)
    } catch (e) {
      if (e instanceof ValidationError) {
        if (e.errors) {
          e.errors.forEach((err) => {
            const [_body, ...rest] = err.loc
            errors[rest.join('-')] = err.msg
          })
        } else {
          errors['unexpected'] = e.message
        }
      } else {
        useToast((e as Error).message, 6000, 'error')
      }
    }
  }

  return { form, items, errors, onSubmit }
}
