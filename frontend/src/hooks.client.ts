import { goto } from '$app/navigation'
import { resolve } from '$app/paths'
import { TOTP_SETUP_PATH, UnauthorizedError, isTotpSetupRequired } from '$lib/fastapi-client'
import type { HandleClientError } from '@sveltejs/kit'

// Catches UnauthorizedError thrown by any load() before the root layout's
// onMount registers the redirect/modal handler (e.g. on first navigation),
// so we don't fall through to the generic error page.
export const handleError: HandleClientError = ({ error }) => {
  if (isTotpSetupRequired(error)) {
    // A page load can reach the backend before the admin layout's redirect.
    goto(resolve(TOTP_SETUP_PATH))
    return
  }
  if (error instanceof UnauthorizedError) {
    goto(resolve(`/login?redirect=${encodeURIComponent(location.pathname)}`))
    return
  }
  console.error(error)
}
