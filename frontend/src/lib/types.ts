export interface Model {
  id: string
  simple_name: string
  organisation: string
  icon_path: string
  excerpt: string
  license: string
  distribution: 'open-source' | 'open-weights' | 'proprietary'
  fully_open_source?: boolean
  params: number
  friendly_size: 'XS' | 'S' | 'M' | 'L' | 'XL'
  release_date: string
  // TODO: rename to url or rename .url in APIBotModel
  link?: string
}

// import type { APIBotModel } from '$lib/models';

// export type Model = APIBotModel;

export interface ModelFilters {
  sizes: string[]
  orgs: string[]
  licenses: string[]
}
