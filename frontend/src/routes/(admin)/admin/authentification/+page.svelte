<script lang="ts">
  import { Button, Checkbox, Input, Select } from '$components/dsfr'
  import { PageLayout } from '$components/layout'
  import { api } from '$lib/fastapi-client'
  import type {
    AppSettingsPatch,
    AppSettingsPublic,
    OIDCConnectionTest
  } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { onMount } from 'svelte'

  let loading = $state(true)
  let saving = $state(false)
  let uploadingOidcLogo = $state(false)

  let accessPolicy = $state<'anonymous_first' | 'sign_in_required'>('anonymous_first')
  let domainAllowlist = $state('')
  let methodEmailCode = $state(true)
  let methodOidc = $state(false)

  let oidcIssuer = $state('')
  let oidcClientId = $state('')
  let oidcClientSecret = $state('')
  let oidcHasClientSecret = $state(false)
  let oidcReplaceSecret = $state(false)
  let oidcScopes = $state('')
  let oidcButtonLabel = $state('')
  let oidcHasButtonLogo = $state(false)
  let oidcLogoVersion = $state(0)

  // What the server holds, to tell edits not saved yet from the config the
  // connection test ran against.
  let savedIssuer = $state('')
  let savedClientId = $state('')
  let savedEmailCode = $state(true)
  let connectionTest = $state<OIDCConnectionTest | null>(null)
  let testingConnection = $state(false)

  const connectionTestReasons: Record<string, () => string> = {
    incomplete_config: () => m['admin.settings.oidc.test.reasons.incomplete_config'](),
    secret_unreadable: () => m['admin.settings.oidc.test.reasons.secret_unreadable'](),
    discovery_unreachable: () => m['admin.settings.oidc.test.reasons.discovery_unreachable'](),
    discovery_invalid: () => m['admin.settings.oidc.test.reasons.discovery_invalid'](),
    issuer_mismatch: () => m['admin.settings.oidc.test.reasons.issuer_mismatch'](),
    endpoint_not_https: () => m['admin.settings.oidc.test.reasons.endpoint_not_https'](),
    missing_endpoint: () => m['admin.settings.oidc.test.reasons.missing_endpoint']()
  }

  // The test ran on the saved config: editing the provider fields here makes
  // it say nothing about what would be saved.
  const providerEdited = $derived(
    oidcIssuer.trim() !== savedIssuer ||
      oidcClientId.trim() !== savedClientId ||
      oidcClientSecret.trim() !== ''
  )
  const connectionTestPassed = $derived(!!connectionTest?.passed && !providerEdited)
  // Without the email code, SSO is the only way in: it stays until the
  // provider is shown to work. The backend enforces the same rule.
  const emailCodeLocked = $derived(savedEmailCode && methodOidc && !connectionTestPassed)

  let errors = $state<Record<string, string>>({})

  function applySaved(data: AppSettingsPublic) {
    savedIssuer = data.oidc_issuer ?? ''
    savedClientId = data.oidc_client_id ?? ''
    savedEmailCode = data.auth_methods.includes('email_code')
    connectionTest = data.oidc_connection_test ?? null
  }

  async function load() {
    loading = true
    try {
      const data = await api.request<AppSettingsPublic>('/admin/settings')
      accessPolicy = data.auth_access_policy
      domainAllowlist = data.auth_domain_allowlist.join(', ')
      methodEmailCode = data.auth_methods.includes('email_code')
      methodOidc = data.auth_methods.includes('oidc')
      oidcIssuer = data.oidc_issuer ?? ''
      oidcClientId = data.oidc_client_id ?? ''
      oidcHasClientSecret = data.oidc_has_client_secret
      oidcScopes = data.oidc_scopes.join(' ')
      oidcButtonLabel = data.oidc_button_label ?? ''
      oidcHasButtonLogo = data.oidc_has_button_logo
      applySaved(data)
    } finally {
      loading = false
    }
  }

  onMount(load)

  function parseScopes() {
    return oidcScopes.split(' ').filter(Boolean)
  }

  function validate() {
    const nextErrors: Record<string, string> = {}
    if (!methodEmailCode && !methodOidc) {
      nextErrors.authMethods = m['admin.settings.authentification.authMethods.error']()
    }
    if (methodOidc) {
      if (!oidcIssuer.trim()) {
        nextErrors.oidcIssuer = m['admin.settings.oidc.issuer.required']()
      }
      if (!oidcClientId.trim()) {
        nextErrors.oidcClientId = m['admin.settings.oidc.clientId.required']()
      }
      const needSecret = !oidcHasClientSecret || oidcReplaceSecret
      if (needSecret && !oidcClientSecret.trim()) {
        nextErrors.oidcSecret = m['admin.settings.oidc.clientSecret.required']()
      }
      if (!parseScopes().includes('openid')) {
        nextErrors.oidcScopes = m['admin.settings.oidc.scopes.openidRequired']()
      }
    }
    errors = nextErrors
    return Object.keys(nextErrors).length === 0
  }

  async function save(e: SubmitEvent) {
    e.preventDefault()
    if (!validate()) return
    saving = true
    try {
      const authMethods: string[] = []
      if (methodEmailCode) authMethods.push('email_code')
      if (methodOidc) authMethods.push('oidc')

      const patch: AppSettingsPatch = {
        auth_access_policy: accessPolicy,
        auth_domain_allowlist: domainAllowlist
          .split(',')
          .map((d) => d.trim())
          .filter(Boolean),
        auth_methods: authMethods
      }

      // Unticking OIDC only removes it from the methods: the provider config
      // stays stored so it can be re-enabled without typing it again.
      if (methodOidc) {
        patch.oidc_issuer = oidcIssuer.trim() || null
        patch.oidc_client_id = oidcClientId.trim() || null
        patch.oidc_scopes = parseScopes()
        patch.oidc_button_label = oidcButtonLabel.trim() || null
        if ((!oidcHasClientSecret || oidcReplaceSecret) && oidcClientSecret.trim()) {
          patch.oidc_client_secret = oidcClientSecret.trim()
        }
      }

      const saved = await api.request<AppSettingsPublic>('/admin/settings', {
        method: 'PATCH',
        body: JSON.stringify(patch)
      })

      accessPolicy = saved.auth_access_policy
      domainAllowlist = saved.auth_domain_allowlist.join(', ')
      methodEmailCode = saved.auth_methods.includes('email_code')
      methodOidc = saved.auth_methods.includes('oidc')
      oidcIssuer = saved.oidc_issuer ?? ''
      oidcClientId = saved.oidc_client_id ?? ''
      oidcHasClientSecret = saved.oidc_has_client_secret
      oidcReplaceSecret = false
      oidcClientSecret = ''
      oidcScopes = saved.oidc_scopes.join(' ')
      oidcButtonLabel = saved.oidc_button_label ?? ''
      oidcHasButtonLogo = saved.oidc_has_button_logo
      applySaved(saved)

      useToast(m['admin.settings.saved'](), 4000)
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      saving = false
    }
  }

  async function testConnection() {
    testingConnection = true
    try {
      connectionTest = await api.request<OIDCConnectionTest>('/admin/settings/oidc/test', {
        method: 'POST'
      })
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      testingConnection = false
    }
  }

  async function uploadOidcLogo(e: Event) {
    const input = e.currentTarget as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return
    uploadingOidcLogo = true
    try {
      const formData = new FormData()
      formData.append('file', file)
      await api.request('/admin/settings/oidc-logo', { method: 'PUT', body: formData, headers: {} })
      oidcHasButtonLogo = true
      oidcLogoVersion++
      useToast(m['admin.settings.oidc.buttonLogo.updated'](), 4000)
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      uploadingOidcLogo = false
      input.value = ''
    }
  }

  async function resetOidcLogo() {
    uploadingOidcLogo = true
    try {
      await api.request('/admin/settings/oidc-logo', { method: 'DELETE', headers: {} })
      oidcHasButtonLogo = false
      oidcLogoVersion++
      useToast(m['admin.settings.oidc.buttonLogo.resetDone'](), 4000)
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      uploadingOidcLogo = false
    }
  }
</script>

<PageLayout
  seoTitle={m['admin.nav.authentification']()}
  title={m['admin.nav.authentification']()}
  subtitle={m['admin.settings.subtitle']()}
>
  {#if loading}
    <p class="fr-text--sm text-[--text-mention-grey]">{m['admin.settings.loading']()}</p>
  {:else}
    <form id="settings-auth-form" onsubmit={save} class="max-w-[480px]">
      <Select
        id="settings-access-policy"
        label={m['admin.settings.authentification.accessPolicy.label']()}
        bind:selected={accessPolicy}
        options={[
          {
            value: 'anonymous_first',
            label: m['admin.settings.authentification.accessPolicy.anonymous']()
          },
          {
            value: 'sign_in_required',
            label: m['admin.settings.authentification.accessPolicy.required']()
          }
        ]}
      />
      <Input
        id="settings-domain-allowlist"
        label={m['admin.settings.authentification.domainAllowlist.label']()}
        help={m['admin.settings.authentification.domainAllowlist.help']()}
        bind:value={domainAllowlist}
        groupClass="mt-4!"
      />

      <div class="mt-6!">
        <p class="fr-label mb-2!">{m['admin.settings.authentification.authMethods.label']()}</p>
        {#if errors.authMethods}
          <p class="fr-message fr-message--error mb-2!" id="settings-auth-methods-error">
            {errors.authMethods}
          </p>
        {/if}
        <Checkbox
          id="settings-method-email-code"
          label={m['admin.settings.authentification.authMethods.emailCode']()}
          bind:checked={methodEmailCode}
          disabled={emailCodeLocked}
          help={emailCodeLocked
            ? m['admin.settings.authentification.authMethods.emailCodeLocked']()
            : undefined}
        />
        <Checkbox
          id="settings-method-oidc"
          label={m['admin.settings.authentification.authMethods.oidc']()}
          bind:checked={methodOidc}
        />
      </div>

      {#if methodOidc}
        <fieldset id="settings-oidc-config" class="mt-6! p-0 border-0">
          <legend class="fr-h5">{m['admin.settings.oidc.title']()}</legend>

          <Input
            id="settings-oidc-issuer"
            label={m['admin.settings.oidc.issuer.label']()}
            help={m['admin.settings.oidc.issuer.hint']()}
            bind:value={oidcIssuer}
            error={errors.oidcIssuer}
            groupClass="mt-2!"
          />

          <Input
            id="settings-oidc-client-id"
            label={m['admin.settings.oidc.clientId.label']()}
            bind:value={oidcClientId}
            error={errors.oidcClientId}
            groupClass="mt-4!"
          />

          <div class="mt-4!" id="settings-oidc-secret-wrapper">
            {#if oidcHasClientSecret && !oidcReplaceSecret}
              <p class="fr-label mb-1!">{m['admin.settings.oidc.clientSecret.label']()}</p>
              <div class="gap-3 flex items-center">
                <span
                  id="settings-oidc-secret-masked"
                  class="fr-text--sm text-[--text-mention-grey]">••••••••••••</span
                >
                <button
                  type="button"
                  id="settings-oidc-secret-replace"
                  class="fr-btn fr-btn--tertiary fr-btn--sm"
                  onclick={() => {
                    oidcReplaceSecret = true
                    oidcClientSecret = ''
                  }}
                >
                  {m['admin.settings.oidc.clientSecret.replace']()}
                </button>
              </div>
            {:else}
              <!-- "Leave empty to keep the current value" only makes sense
                   when there is a stored value to keep. -->
              <Input
                id="settings-oidc-secret"
                type="password"
                autocomplete="off"
                label={m['admin.settings.oidc.clientSecret.label']()}
                help={oidcHasClientSecret
                  ? m['admin.settings.oidc.clientSecret.hint']()
                  : undefined}
                bind:value={oidcClientSecret}
                error={errors.oidcSecret}
              />
            {/if}
          </div>

          <Input
            id="settings-oidc-scopes"
            label={m['admin.settings.oidc.scopes.label']()}
            help={m['admin.settings.oidc.scopes.hint']()}
            bind:value={oidcScopes}
            error={errors.oidcScopes}
            groupClass="mt-4!"
          />

          <Input
            id="settings-oidc-button-label"
            label={m['admin.settings.oidc.buttonLabel.label']()}
            help={m['admin.settings.oidc.buttonLabel.hint']()}
            bind:value={oidcButtonLabel}
            groupClass="mt-4!"
          />

          <div class="mt-4!">
            <Button
              type="button"
              id="settings-oidc-test"
              variant="secondary"
              size="sm"
              text={testingConnection
                ? m['admin.settings.oidc.test.running']()
                : m['admin.settings.oidc.test.button']()}
              disabled={testingConnection || providerEdited || !savedIssuer || !oidcHasClientSecret}
              onclick={testConnection}
            />
            {#if providerEdited}
              <p id="settings-oidc-test-hint" class="fr-hint-text mt-1!">
                {m['admin.settings.oidc.test.hint']()}
              </p>
            {:else if connectionTest}
              <p
                role="status"
                class="fr-message mt-2! {connectionTest.passed
                  ? 'fr-message--valid'
                  : 'fr-message--error'}"
              >
                {#if connectionTest.passed}
                  {m['admin.settings.oidc.test.passed']()}
                {:else}
                  {m['admin.settings.oidc.test.failed']({
                    reason: connectionTestReasons[connectionTest.reason ?? '']?.() ?? ''
                  })}
                {/if}
              </p>
            {/if}
          </div>

          <div class="mt-4!">
            <p class="fr-label mb-2!">{m['admin.settings.oidc.buttonLogo.label']()}</p>
            <div class="gap-4 flex items-center">
              {#if oidcHasButtonLogo}
                <img
                  src={api.getUrl('/auth/config/oidc/logo', { v: oidcLogoVersion.toString() })}
                  alt=""
                  class="h-[32px] border border-[--border-default-grey]"
                />
              {/if}
              <div class="gap-2 flex flex-col">
                <label class="fr-label">
                  <span class="fr-sr-only">{m['admin.settings.oidc.buttonLogo.label']()}</span>
                  <input
                    class="fr-upload"
                    type="file"
                    accept="image/png,image/jpeg,image/svg+xml,image/webp"
                    disabled={uploadingOidcLogo}
                    onchange={uploadOidcLogo}
                  />
                </label>
                {#if oidcHasButtonLogo}
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    text={m['admin.settings.oidc.buttonLogo.reset']()}
                    disabled={uploadingOidcLogo}
                    onclick={resetOidcLogo}
                  />
                {/if}
              </div>
            </div>
            <p class="fr-hint-text mt-1!">{m['admin.settings.oidc.buttonLogo.hint']()}</p>
          </div>
        </fieldset>
      {/if}

      <Button
        type="submit"
        text={saving ? m['admin.settings.saving']() : m['admin.settings.save']()}
        disabled={saving}
        class="mt-6!"
      />
    </form>
  {/if}
</PageLayout>
