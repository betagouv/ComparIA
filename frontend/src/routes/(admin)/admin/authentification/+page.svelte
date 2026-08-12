<script lang="ts">
  import { Button, Checkbox, Input, Select } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { api } from '$lib/fastapi-client'
  import type { AppSettingsPatch, AppSettingsPublic } from '$lib/generated/admin'
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

  let errors = $state<Record<string, string>>({})

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
    } finally {
      loading = false
    }
  }

  onMount(load)

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
        auth_methods: authMethods,
        oidc_issuer: methodOidc ? oidcIssuer.trim() || null : null,
        oidc_client_id: methodOidc ? oidcClientId.trim() || null : null,
        oidc_scopes: methodOidc ? oidcScopes.split(' ').filter(Boolean) : [],
        oidc_button_label: methodOidc ? oidcButtonLabel.trim() || null : null
      }

      if (methodOidc && (!oidcHasClientSecret || oidcReplaceSecret) && oidcClientSecret.trim()) {
        patch.oidc_client_secret = oidcClientSecret.trim()
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

      useToast(m['admin.settings.saved'](), 4000)
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      saving = false
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
            <p class="fr-label mb-1!">{m['admin.settings.oidc.clientSecret.label']()}</p>
            {#if oidcHasClientSecret && !oidcReplaceSecret}
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
              <input
                id="settings-oidc-secret"
                type="password"
                autocomplete="off"
                class="fr-input"
                aria-describedby={errors.oidcSecret ? 'settings-oidc-secret-error' : undefined}
                aria-invalid={errors.oidcSecret ? 'true' : undefined}
                bind:value={oidcClientSecret}
              />
              {#if errors.oidcSecret}
                <p class="fr-message fr-message--error" id="settings-oidc-secret-error">
                  {errors.oidcSecret}
                </p>
              {/if}
              <p class="fr-hint-text mt-1!">{m['admin.settings.oidc.clientSecret.hint']()}</p>
            {/if}
          </div>

          <Input
            id="settings-oidc-scopes"
            label={m['admin.settings.oidc.scopes.label']()}
            help={m['admin.settings.oidc.scopes.hint']()}
            bind:value={oidcScopes}
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
            <p class="fr-label mb-2!">{m['admin.settings.oidc.buttonLogo.label']()}</p>
            <div class="gap-4 flex items-center">
              {#if oidcHasButtonLogo}
                <img
                  src="{api.getUrl('/admin/settings/oidc-logo')}?v={oidcLogoVersion}"
                  alt=""
                  class="h-[32px] border border-[--border-default-grey]"
                />
              {/if}
              <div class="gap-2 flex flex-col">
                <label class="fr-label">
                  <span class="fr-sr-only">{m['admin.settings.oidc.buttonLogo.label']()}</span>
                  <input
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
