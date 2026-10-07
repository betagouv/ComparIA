import type { AuthConfig } from '$lib/authContext.svelte'
import { api } from '$lib/fastapi-client'
import { m } from '$lib/i18n/messages'

export type SignInTab = { id: 'email' | 'sso'; label: string }

/**
 * What the sign-in modal and the login page offer, derived once from the public
 * auth config. The server derives `oidc_enabled` from `methods` plus a usable
 * provider config, so the SSO button only shows when OIDC would actually work.
 * Email code is assumed on until the config says otherwise.
 */
export function signInMethods(config: Partial<AuthConfig> | undefined) {
  const oidcEnabled = config?.oidc_enabled ?? false
  const emailEnabled = config?.methods?.includes('email_code') ?? true
  // One tab per enabled method; with a single method there is nothing to
  // switch between, so callers render no tabs at all.
  const tabs: SignInTab[] = []
  if (emailEnabled) tabs.push({ id: 'email', label: m['auth.login.tabEmail']() })
  if (oidcEnabled) tabs.push({ id: 'sso', label: m['auth.login.tabSso']() })
  return {
    oidcEnabled,
    emailEnabled,
    bothMethods: oidcEnabled && emailEnabled,
    oidcLabel: config?.oidc_button_label || m['auth.oidc.buttonFallback'](),
    oidcLogoUrl: config?.oidc_has_button_logo ? api.getUrl('/auth/config/oidc/logo') : null,
    tabs
  }
}
