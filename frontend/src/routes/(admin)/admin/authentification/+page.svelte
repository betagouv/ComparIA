<script lang="ts">
  import { Button, Input, Select } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { api } from '$lib/fastapi-client'
  import type { AppSettingsPatch, AppSettingsPublic } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { onMount } from 'svelte'

  let loading = $state(true)
  let saving = $state(false)

  let accessPolicy = $state<'anonymous_first' | 'sign_in_required'>('anonymous_first')
  let domainAllowlist = $state('')

  async function load() {
    loading = true
    try {
      const data = await api.request<AppSettingsPublic>('/admin/settings')
      accessPolicy = data.auth_access_policy
      domainAllowlist = data.auth_domain_allowlist.join(', ')
    } finally {
      loading = false
    }
  }

  onMount(load)

  async function save(e: SubmitEvent) {
    e.preventDefault()
    saving = true
    try {
      const patch: AppSettingsPatch = {
        auth_access_policy: accessPolicy,
        auth_domain_allowlist: domainAllowlist
          .split(',')
          .map((domain) => domain.trim())
          .filter(Boolean)
      }
      await api.request('/admin/settings', { method: 'PATCH', body: JSON.stringify(patch) })
      useToast(m['admin.settings.saved'](), 4000)
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      saving = false
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
    <form onsubmit={save} class="max-w-[480px]">
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
      <Button
        type="submit"
        text={saving ? m['admin.settings.saving']() : m['admin.settings.save']()}
        disabled={saving}
        class="mt-4!"
      />
    </form>
  {/if}
</PageLayout>
