import type { LegalStatuses } from '$lib/generated/admin'
import { render, within } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import type { PageData } from './$types'
import Page from './+page.svelte'

const done = { published: true, missing_locales: false }
const status: LegalStatuses = {
  participation: done,
  cookies: { published: false, missing_locales: false },
  terms: done,
  privacy_policy: done,
  legal_notice: done,
  accessibility: done,
  ecodesign: done
}

describe('legal hub', () => {
  it('lists the cookies page as off, not to complete, while the switch is off', () => {
    const { getByRole } = render(Page, { data: { status } as unknown as PageData, params: {} })

    const link = getByRole('link', { name: 'Cookies et mesure d’audience' })
    expect(link).toHaveAttribute('href', '/admin/legal/cookies')
    expect(within(link.closest('tr')!).getByText('Désactivé')).toBeInTheDocument()
    expect(within(link.closest('tr')!).queryByText('À compléter')).toBeNull()
  })
})
