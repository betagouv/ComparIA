import type { ApiError } from '$lib/fastapi-client'
import { m } from '$lib/i18n/messages'

/** The backend's error keys about selection modes, in plain words. */
export const MODE_ERRORS: Record<string, () => string> = {
  mode_not_found: m['admin.selectionModes.errors.notFound'],
  mode_key_taken: m['admin.selectionModes.errors.keyTaken'],
  mode_key_immutable: m['admin.selectionModes.errors.keyImmutable'],
  last_enabled_mode: m['admin.selectionModes.errors.lastEnabled'],
  default_mode_changed: m['admin.selectionModes.errors.defaultChanged'],
  label_missing_default_locale: m['admin.selectionModes.errors.labelDefaultLocale'],
  label_required: m['admin.selectionModes.errors.labelRequired'],
  forced_tools_required: m['admin.selectionModes.errors.forcedTools'],
  invalid_window: m['admin.selectionModes.errors.window'],
  invalid_params_range: m['admin.selectionModes.errors.paramsRange'],
  invalid_release_range: m['admin.selectionModes.errors.releaseRange'],
  invalid_tag: m['admin.selectionModes.errors.tag'],
  string_pattern_mismatch: m['admin.selectionModes.errors.pattern'],
  greater_than_equal: m['admin.selectionModes.errors.tooSmall']
}

// Errors about two fields, or about the whole mode, show next to the field
// the admin should change.
export const MODE_ERROR_FIELDS: Record<string, string> = {
  mode_key_taken: 'key',
  mode_key_immutable: 'key',
  last_enabled_mode: 'enabled',
  default_mode_changed: 'is_default',
  invalid_params_range: 'params_max',
  invalid_release_range: 'released_before',
  invalid_window: 'ends_at',
  forced_tools_required: 'tool_keys',
  label_required: 'label'
}

/** A validation error in plain words, when its key is known. */
export function errorText(error: { msg: string; type?: string }): string {
  const known = MODE_ERRORS[error.msg] ?? (error.type ? MODE_ERRORS[error.type] : undefined)
  return known ? known() : error.msg
}

/** What a failed request means for the admin, whatever its status. */
export function requestErrorText(error: unknown): string {
  const detail = (error as ApiError).detail
  if (typeof detail === 'string') return MODE_ERRORS[detail]?.() ?? detail
  return (error as Error).message
}
