import type { LLMData, LLMLabPublic, LLMLicense, ModelFilter } from '$lib/generated/admin'
import type { Lookups } from './summary'

export type Choice = { value: string; label: string; hint?: string }

/** What the filter builder offers to pick from. */
export type Catalogue = {
  llmChoices: Choice[]
  labChoices: Choice[]
  licenseChoices: Choice[]
  /** Tags already set on at least one model. */
  tags: string[]
}

type Catalog = { llms: LLMData[]; labs: LLMLabPublic[]; licenses: LLMLicense[] }

const byLabel = (a: Choice, b: Choice) => a.label.localeCompare(b.label)

export function buildCatalogue({ llms, labs, licenses }: Catalog): Catalogue {
  const labName = new Map(labs.map((lab) => [lab.id!, lab.name]))
  return {
    // Only models the arena can draw. One that was switched off since it was
    // picked still shows as a chip, from the lookups.
    llmChoices: llms
      .filter((llm) => llm.status === 'enabled')
      .map((llm) => ({ value: llm.id!, label: llm.name, hint: labName.get(llm.lab_id) }))
      .sort(byLabel),
    labChoices: labs.map((lab) => ({ value: lab.id!, label: lab.name })).sort(byLabel),
    licenseChoices: licenses
      .map((license) => ({ value: license.id!, label: license.name }))
      .sort(byLabel),
    tags: [...new Set(llms.flatMap((llm) => llm.tags ?? []))].sort()
  }
}

export function buildLookups({ llms, labs, licenses }: Catalog): Lookups {
  return {
    llms: new Map(llms.map((llm) => [llm.id!, llm.name])),
    labs: new Map(labs.map((lab) => [lab.id!, lab.name])),
    licenses: new Map(licenses.map((license) => [license.id!, license.name]))
  }
}

/** A yes / no / either choice, as the value of a radio input. */
export const triState = {
  toInput(value: boolean | null | undefined): string {
    return value == null ? '' : String(value)
  },
  fromInput(input: string): boolean | null {
    return input === '' ? null : input === 'true'
  }
}

/** The filter without the given criterion. */
export function clearCriterion(filter: ModelFilter, fields: (keyof ModelFilter)[]): ModelFilter {
  const next = { ...filter }
  for (const field of fields) delete next[field]
  return next
}
