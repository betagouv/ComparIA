import { api, ValidationError, type ApiError } from '$lib/fastapi-client'
import { useToast } from '$lib/helpers/useToast.svelte'
import { m } from '$lib/i18n/messages'
import { getKeys, omit } from '$lib/utils/commons'
import { getFormFields, getSchemaDefaults, type JSONSchema } from '$lib/utils/form'
import { untrack } from 'svelte'

export type FormErrors = Record<string, string>

export function resetFormErrors(errorsState: FormErrors) {
  getKeys(errorsState).forEach((k) => delete errorsState[k])
}

export type FormErrorOptions = {
  // Text for a backend error key, sent as a `detail` or as a validation
  // error's type or message
  errorMessages?: Record<string, () => string>
  // The field an error about several fields, or about the whole body, is
  // shown on, by error key
  errorFields?: Record<string, string>
}

function knownKey(keys: (string | undefined)[], { errorMessages, errorFields }: FormErrorOptions) {
  return keys.find((key) => key && (key in (errorMessages ?? {}) || key in (errorFields ?? {})))
}

export function updateFormErrors(
  error: ValidationError,
  errorsState: FormErrors,
  options: FormErrorOptions = {}
) {
  if (error.errors) {
    error.errors.forEach((err) => {
      const key = knownKey([err.msg, err.type], options)
      const field = key ? options.errorFields?.[key] : undefined
      // A model validator adds its own name to the location
      const path = err.loc
        .slice(1)
        .map(String)
        .filter((part) => !part.startsWith('function-') && part !== field)
      if (field) path.push(field)
      errorsState[path.join('-') || 'unexpected'] = key
        ? (options.errorMessages?.[key]?.() ?? err.msg)
        : err.msg
    })
  } else {
    errorsState['unexpected'] = error.message
  }
}

/** Shows a known backend `detail` in the form. False for any other error. */
export function updateFormDetailError(
  error: unknown,
  errorsState: FormErrors,
  options: FormErrorOptions = {}
): boolean {
  const detail = (error as ApiError).detail
  const key = typeof detail === 'string' ? knownKey([detail], options) : undefined
  if (!key) return false
  errorsState[options.errorFields?.[key] ?? 'unexpected'] = options.errorMessages?.[key]?.() ?? key
  return true
}

type UseFormOptions<T extends object, K extends keyof T = never> = {
  url: string
  initialData: () => T
  omitKeys?: K[]
  method?: 'post' | 'put' | 'PATCH'
  // Returns the body to send, which may differ from the form, or null to stop
  onBeforeSubmit?: (form: Omit<T, K>, errors: FormErrors) => object | null | Promise<object | null>
  onSuccess?: (form: Omit<T, K>) => void | Promise<void>
} & FormErrorOptions

export function useForm<T extends object, K extends keyof T = never>({
  url,
  initialData: _initialData,
  omitKeys,
  method,
  onBeforeSubmit,
  onSuccess,
  ...errorOptions
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
      const body = await (onBeforeSubmit
        ? onBeforeSubmit($state.snapshot(form) as Omit<T, K>, errors)
        : form)
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
        updateFormErrors(e, errors, errorOptions)
        useToast(m['form.toastError'](), 6000, 'error')
      } else if (updateFormDetailError(e, errors, errorOptions)) {
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
