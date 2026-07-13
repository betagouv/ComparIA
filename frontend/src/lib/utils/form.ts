import type {
  FormCheckboxGroupProps,
  FormCheckboxProps,
  FormFieldsetItemProps,
  FormFieldsetListProps,
  FormInputProps,
  FormSelectProps,
  FormToggleProps
} from '$components/form'
export type AnyFormItemComponent =
  | 'input'
  | 'select'
  | 'toggle'
  | 'checkbox'
  | 'checkbox-group'
  | 'fieldset'
  | 'fieldset-item'
  | 'fieldset-list'

export type BaseFormFieldProps<C extends AnyFormItemComponent, T = any> = {
  id: string
  label: string
  value: T
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
