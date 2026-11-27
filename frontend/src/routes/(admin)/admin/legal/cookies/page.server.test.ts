import { afterEach, describe, expect, it, vi } from 'vitest'
import { load } from './+page.server'

const privateEnv = vi.hoisted(() => ({}) as Record<string, string | undefined>)
vi.mock('$env/dynamic/private', () => ({ env: privateEnv }))

const runLoad = () => load({} as Parameters<typeof load>[0])

describe('cookies admin page server load', () => {
  afterEach(() => {
    delete privateEnv.MATOMO_URL
    delete privateEnv.MATOMO_ID
  })

  it('passes on the Matomo the server was given', () => {
    privateEnv.MATOMO_URL = 'https://stats.example.org'
    privateEnv.MATOMO_ID = '12'

    expect(runLoad()).toEqual({
      serverMatomo: { MATOMO_URL: 'https://stats.example.org', MATOMO_ID: '12' }
    })
  })

  it('passes on empty values when the server has no Matomo', () => {
    expect(runLoad()).toEqual({ serverMatomo: { MATOMO_URL: '', MATOMO_ID: '' } })
  })
})
