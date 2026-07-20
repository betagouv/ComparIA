import { goto } from '$app/navigation'
import { resolve } from '$app/paths'
import { UnauthorizedError } from '$lib/fastapi-client'
import type { HandleClientError } from '@sveltejs/kit'

// Catches UnauthorizedError thrown by any load() before the root layout's
// onMount registers the redirect/modal handler (e.g. on first navigation),
// so we don't fall through to the generic error page.
export const handleError: HandleClientError = ({ error }) => {
  if (error instanceof UnauthorizedError && error.message === 'auth_required') {
    goto(resolve(`/login?redirect=${encodeURIComponent(location.pathname)}`))
    return
  }
  console.error(error)
}
