// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
  namespace App {
    // interface Error {}
    interface Locals {
      // Read from the instance config on every server render.
      cookieBannerEnabled: boolean
    }
    // interface PageData {}
    // interface PageState {}
    // interface Platform {}
  }
}

export {}
