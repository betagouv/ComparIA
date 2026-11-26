import type { LayoutServerLoad } from './$types'

// The switch and the measurement the server rendered this page with, so the
// browser shows the banner exactly when the server held Matomo back.
export const load: LayoutServerLoad = ({ locals }) => ({
  cookieBannerEnabled: locals.cookieBannerEnabled,
  measurement: locals.measurement
})
