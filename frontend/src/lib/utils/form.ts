import type {
  FormCheckboxGroupProps,
  FormCheckboxProps,
  FormFieldsetItemProps,
  FormFieldsetListProps,
  FormInputProps,
  FormSelectProps,
  FormToggleProps
} from '$components/form'
import { getKeys, tryI18n } from '$lib/utils/commons'
import type { JSONSchema7 as BaseJSONSchema } from 'json-schema'

export type JSONSchema = BaseJSONSchema & {
  id: PropertyKey
  properties?: Record<string, JSONSchema>
  required: string[]
  $defs: Record<string, JSONSchema>
  optional?: boolean
}

export type AnyFormItemComponent =
  | 'input'
  | 'select'
  | 'toggle'
  | 'checkbox'
  | 'checkbox-group'
  | 'fieldset'
  | 'fieldset-item'
  | 'fieldset-list'

export type BaseFormFieldProps<C extends AnyFormItemComponent, T> = {
  id: string
  label: string
  value: T
  required?: boolean
  component: C
  help?: string
  errors?: Record<string, string>
}

export type Option<T> = { value: T; label: string }

export type AnyFormItemProps =
  | FormInputProps
  | FormSelectProps
  | FormToggleProps
  | FormCheckboxProps
  | FormCheckboxGroupProps
  | FormFieldsetItemProps
  | FormFieldsetListProps

function parseSchema(
  schema: JSONSchema,
  id: string,
  i18nBaseKey?: string
): AnyFormItemProps | AnyFormItemProps[] {
  const { properties, $defs, type, $ref, enum: $enum, optional } = schema
  const label = tryI18n(`${i18nBaseKey}.${id}.label`, schema.title)
  const help = tryI18n(`${i18nBaseKey}.${id}.help`, schema.description)
  const baseProps = {
    id,
    label,
    help,
    required: !optional,
    value: 'placeholder' as any
  } // FIXME value to remove

  if (type === 'object') {
    if (!properties) throw new Error('no properties')

    const subProps = getKeys(properties).map((k) => {
      if (typeof properties[k] === 'boolean') throw new Error('property err')

      return parseSchema({ ...properties[k], $defs }, k as string, i18nBaseKey)
    }) as AnyFormItemProps[]
    if (id) {
      return {
        ...baseProps,
        component: 'fieldset-item',
        subProps
      }
    } else {
      return subProps
    }
  } else if ($ref) {
    const ref = $ref.replace('#/$defs/', '')
    if (!$defs || !(ref in $defs) || typeof $defs[ref] === 'boolean') throw new Error('defs err')
    const innerSchema = { ...$defs[ref], $defs }
    return parseSchema(innerSchema, id, `${i18nBaseKey}.${ref}`)
  } else if ($enum) {
    const options = $enum.map((value) =>
      typeof value === 'string'
        ? { label: value as string, value: value as string }
        : (value as unknown as Option<string | null>)
    )
    if (optional) {
      options.push({ value: null, label: 'None' })
    }
    return {
      ...baseProps,
      component: 'select',
      options
    }
  } else if (type === 'string') {
    const types = {
      'date-time': 'date',
      uri: 'url',
      default: 'text'
    }
    const format =
      schema.format && schema.format in types ? (schema.format as keyof typeof types) : 'default'
    return { ...baseProps, component: 'input', type: types[format] }
  } else if (type === 'boolean') {
    return { ...baseProps, component: 'toggle' }
  } else if (type === 'integer' || type === 'number') {
    return {
      ...baseProps,
      component: 'input',
      type: 'number',
      step: schema.type === 'integer' ? '1' : '0.0001'
    }
  } else if (type === 'array') {
    const inner = schema.items
    if (!inner || typeof inner === 'boolean' || Array.isArray(inner))
      throw new Error('not implemented')
    if (inner.enum) {
      return {
        ...parseSchema({ ...inner, $defs }, id, i18nBaseKey),
        ...baseProps,
        component: 'checkbox-group'
      }
    } else {
      return {
        ...baseProps,
        component: 'fieldset-list',
        subProps: parseSchema({ ...inner, $defs }, id, i18nBaseKey)
      }
    }
  }
  throw new Error('could not parse schema')
}

export function getFormFields(schema: BaseJSONSchema, i18nBaseKey: string) {
  return parseSchema(schema, '', i18nBaseKey) as AnyFormItemProps[]
}
