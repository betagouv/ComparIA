import type { CookieConsentDecision } from '$lib/cookieConsent'

// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
  namespace App {
    // interface Error {}
    interface Locals {
      // Read from the instance config on every server render, null when it
      // has never been read.
      cookieBannerEnabled: boolean | null
      // What that switch and the visitor's answer allow for this request.
      cookieConsent: CookieConsentDecision
    }
    // interface PageData {}
    // interface PageState {}
    // interface Platform {}
  }
}

export {}
