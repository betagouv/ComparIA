import type { PromptCheckCriterion } from '$lib/generated/admin'

/** What every criterion has, whichever check asks it. */
export type CriterionFields = Pick<
  PromptCheckCriterion,
  'key' | 'label' | 'question' | 'yes' | 'no' | 'threshold'
>

/** A readable key from a name, not one of `taken`. */
export function keyFrom(label: string, taken: string[]) {
  const base =
    label
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^[^a-z]+|_+$/g, '')
      .slice(0, 36) || 'critere'
  let key = base
  for (let n = 2; taken.includes(key); n++) key = `${base}_${n}`
  return key
}
