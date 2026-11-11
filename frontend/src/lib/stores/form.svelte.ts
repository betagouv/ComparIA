import { api, ValidationError } from '$lib/fastapi-client'
import { useToast } from '$lib/helpers/useToast.svelte'
import { m } from '$lib/i18n/messages'
import { getKeys, omit } from '$lib/utils/commons'
import { getFormFields, getSchemaDefaults, type JSONSchema } from '$lib/utils/form'
import { untrack } from 'svelte'

export type FormErrors = Record<string, string>

export function resetFormErrors(errorsState: FormErrors) {
  getKeys(errorsState).forEach((k) => delete errorsState[k])
}

export function updateFormErrors(error: ValidationError, errorsState: FormErrors) {
  if (error.errors) {
    error.errors.forEach((err) => {
      const [_body, ...rest] = err.loc
      errorsState[rest.join('-')] = err.msg
    })
  } else {
    errorsState['unexpected'] = error.message
  }
}

type UseFormOptions<T extends object, K extends keyof T = never> = {
  url: string
  initialData: () => T
  omitKeys?: K[]
  method?: 'post' | 'put'
  onBeforeSubmit?: (
    form: Omit<T, K>,
    errors: FormErrors
  ) => Omit<T, K> | null | Promise<Omit<T, K> | null>
  onSuccess?: (form: Omit<T, K>) => void | Promise<void>
}

export function useForm<T extends object, K extends keyof T = never>({
  url,
  initialData: _initialData,
  omitKeys,
  method,
  onBeforeSubmit,
  onSuccess
}: UseFormOptions<T, K>) {
  const initialData = $derived(structuredClone(_initialData()))
  const errors = $state<FormErrors>({})
  const form = $state<Omit<T, K>>(omit(initialData, omitKeys ?? []))

  let isBusy = $state(false)
  let savedBaseline = $state('')
  const isDirty = $derived(JSON.stringify(form) !== savedBaseline)

  $effect(() => {
    Object.assign(form, omit(initialData, omitKeys ?? []))
    untrack(() => {
      savedBaseline = JSON.stringify(form)
    })
  })

  async function onSubmit() {
    resetFormErrors(errors)

    try {
      const body = await (onBeforeSubmit ? onBeforeSubmit(form, errors) : form)
      // onBeforeSubmit consumer can return 'null' to prevent form submit
      if (body === null) {
        useToast(m['form.toastError'](), 6000, 'error')
        return
      }
      isBusy = true
      const updated = await api.request<T>(url, { body: JSON.stringify(body), method })
      useToast(m['form.toastSuccess'](), 5000, 'success')
      savedBaseline = JSON.stringify(form)
      await onSuccess?.(updated)
    } catch (e) {
      if (e instanceof ValidationError) {
        updateFormErrors(e, errors)
        useToast(m['form.toastError'](), 6000, 'error')
      } else {
        useToast((e as Error).message, 6000, 'error')
      }
    } finally {
      isBusy = false
    }
  }

  return {
    form,
    errors,
    onSubmit,
    get isBusy() {
      return isBusy
    },
    get isDirty() {
      return isDirty
    }
  }
}

type UseFormSchemaOptions<T extends object, K extends keyof T = never> = UseFormOptions<T, K> & {
  i18nKey: string
  schema: () => JSONSchema
}

export function useFormSchema<T extends object, K extends keyof T = never>({
  initialData: _initialData,
  schema: _schema,
  i18nKey,
  ...useFormProps
}: UseFormSchemaOptions<T, K>) {
  const initialData = $derived({ ...getSchemaDefaults(_schema()), ..._initialData() })
  const baseForm = useForm<T, K>({ ...useFormProps, initialData: () => initialData })
  const schema = $derived(_schema())
  const items = $derived(
    getFormFields(schema, i18nKey).filter((f) => !useFormProps.omitKeys?.includes(f.id as K))
  )

  return {
    items,
    ...baseForm,
    get isBusy() {
      return baseForm.isBusy
    },
    get isDirty() {
      return baseForm.isDirty
    }
  }
}
