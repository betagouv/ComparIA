<script lang="ts">
  import { Button } from '$components/dsfr'
  import { FormColorInput, FormInput } from '$components/form'
  import Form from '$components/form/Form.svelte'
  import FormTranslate from '$components/form/FormTranslate.svelte'
  import { PageLayout } from '$components/layout'
  import { getAuthContext } from '$lib/auth.svelte'
  import { api } from '$lib/fastapi-client'
  import type { AppSettingsPublic } from '$lib/generated/admin'
  import { getVotesContext } from '$lib/global.svelte'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { useForm, type FormErrors } from '$lib/stores/form.svelte'
  import { contrastRatio, isHexColor } from '$lib/theme'
  import { pick } from '$lib/utils/commons'
  import type { PageProps } from './$types'

  let { data }: PageProps = $props()

  // Same limits as HomeText and HomeBanner in app_settings.py: past them the
  // backend refuses the whole save.
  const HOME_TEXT_MAX_LENGTH = 200
  const HOME_BANNER_MAX_LENGTH = 1000

  // Settings the arena reads from the auth config, refreshed there on save.
  const CONFIG_FIELDS = [
    'platform_name',
    'homepage_url',
    'home_title',
    'home_prompt_placeholder',
    'home_banner',
    'primary_color_light',
    'primary_color_dark',
    'secondary_color_light',
    'secondary_color_dark'
  ] as const
  const FIELDS = [
    ...CONFIG_FIELDS,
    'votes_objective',
    'ranking_min_votes',
    'ranking_max_rank_spread'
  ] as const

  type Settings = Pick<AppSettingsPublic, (typeof FIELDS)[number]>

  const COLORS = [
    { id: 'primary_color_light', label: m['admin.settings.customization.colors.primaryLight']() },
    { id: 'primary_color_dark', label: m['admin.settings.customization.colors.primaryDark']() },
    {
      id: 'secondary_color_light',
      label: m['admin.settings.customization.colors.secondaryLight']()
    },
    { id: 'secondary_color_dark', label: m['admin.settings.customization.colors.secondaryDark']() }
  ] as const

  const auth = getAuthContext()
  const votes = getVotesContext()

  const form = useForm({
    url: '/admin/settings',
    method: 'PATCH',
    initialData: (): Settings => pick(data.settings, FIELDS),
    onBeforeSubmit: (settings, errors) => {
      Object.assign(errors, validate(settings))
      if (Object.keys(errors).length) return null
      return { ...settings, homepage_url: settings.homepage_url || null }
    },
    onSuccess: (saved) => {
      Object.assign(auth.config, pick(saved, CONFIG_FIELDS))
      votes.objective = saved.votes_objective
    }
  })

  function validate(settings: Settings): FormErrors {
    const errors: FormErrors = {}
    for (const { id } of COLORS) {
      if (!isHexColor(settings[id])) {
        errors[id] = m['admin.settings.customization.colors.invalid']()
      }
    }
    if (
      !errors.primary_color_light &&
      contrastRatio(settings.primary_color_light, '#FFFFFF') < 4.5
    ) {
      errors.primary_color_light = m['admin.settings.customization.colors.contrastLight']()
    }
    if (!errors.primary_color_dark && contrastRatio(settings.primary_color_dark, '#161616') < 4.5) {
      errors.primary_color_dark = m['admin.settings.customization.colors.contrastDark']()
    }
    if (settings.homepage_url && !isSecureUrl(settings.homepage_url)) {
      errors.homepage_url = m['admin.settings.customization.homepageUrl.invalid']()
    }
    return errors
  }

  function isSecureUrl(value: string) {
    try {
      const url = new URL(value)
      return url.protocol === 'https:' && !url.username && !url.password && !/\s/.test(value)
    } catch {
      return false
    }
  }

  // The logo is uploaded on its own, outside the form's save.
  let uploadingLogo = $state(false)
  const logoSrc = $derived(
    auth.config.has_custom_logo
      ? api.getPublicUrl('/auth/config/logo', { v: auth.config.logo_version ?? '' })
      : '/orgs/comparia.png'
  )

  async function uploadLogo(e: Event) {
    const input = e.currentTarget as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return

    uploadingLogo = true
    try {
      const formData = new FormData()
      formData.append('file', file)
      const updated = await api.request<AppSettingsPublic>('/admin/settings/logo', {
        method: 'PUT',
        body: formData,
        headers: {}
      })
      auth.config.has_custom_logo = true
      auth.config.logo_version = updated.logo_version ?? null
      useToast(m['admin.settings.customization.logo.updated'](), 4000)
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      uploadingLogo = false
      input.value = ''
    }
  }

  async function resetLogo() {
    uploadingLogo = true
    try {
      await api.request('/admin/settings/logo', { method: 'DELETE', headers: {} })
      auth.config.has_custom_logo = false
      auth.config.logo_version = null
      useToast(m['admin.settings.customization.logo.resetDone'](), 4000)
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      uploadingLogo = false
    }
  }
</script>

<PageLayout
  seoTitle={m['admin.nav.customization']()}
  title={m['admin.nav.customization']()}
  subtitle={m['admin.settings.subtitle']()}
>
  <Form id="customization" {...form} class="max-w-[720px]">
    <FormInput
      id="platform_name"
      type="text"
      label={m['admin.settings.customization.platformName']()}
      errors={form.errors}
      bind:value={form.form.platform_name}
    />

    <FormInput
      id="homepage_url"
      type="url"
      label={m['admin.settings.customization.homepageUrl.label']()}
      help={m['admin.settings.customization.homepageUrl.hint']()}
      placeholder="https://example.gouv.fr"
      errors={form.errors}
      bind:value={form.form.homepage_url}
    />

    <div class="fr-input-group">
      <p class="fr-label font-bold mb-2!">{m['admin.settings.customization.logo.label']()}</p>
      <div class="gap-4 flex items-center">
        <img src={logoSrc} alt="" class="bg-white h-[48px] border border-[--border-default-grey]" />
        <div class="gap-2 flex flex-col">
          <label class="fr-label">
            <span class="fr-sr-only">{m['admin.settings.customization.logo.chooseFile']()}</span>
            <input
              class="fr-upload"
              type="file"
              accept="image/png,image/jpeg,image/svg+xml,image/webp"
              disabled={uploadingLogo}
              onchange={uploadLogo}
            />
          </label>
          {#if auth.config.has_custom_logo}
            <Button
              type="button"
              variant="secondary"
              size="sm"
              text={m['admin.settings.customization.logo.reset']()}
              disabled={uploadingLogo}
              onclick={resetLogo}
            />
          {/if}
        </div>
      </div>
      <p class="fr-hint-text mt-1!">{m['admin.settings.customization.logo.hint']()}</p>
    </div>

    <fieldset class="mt-8! p-0 border-0">
      <legend class="fr-h4">{m['admin.settings.customization.home.title']()}</legend>
      <p class="fr-hint-text mt-0!">{m['admin.settings.customization.home.hint']()}</p>
      <FormTranslate
        id="home_title"
        bind:value={form.form.home_title}
        subProps={{
          component: 'input',
          type: 'text',
          id: 'input',
          maxlength: HOME_TEXT_MAX_LENGTH,
          label: m['admin.settings.customization.home.titleLabel']()
        }}
      />
      <FormTranslate
        id="home_prompt_placeholder"
        bind:value={form.form.home_prompt_placeholder}
        subProps={{
          component: 'input',
          type: 'text',
          id: 'input',
          maxlength: HOME_TEXT_MAX_LENGTH,
          label: m['admin.settings.customization.home.promptPlaceholderLabel']()
        }}
      />
      <FormTranslate
        id="home_banner"
        bind:value={form.form.home_banner}
        subProps={{
          component: 'textarea',
          id: 'input',
          rows: 4,
          maxlength: HOME_BANNER_MAX_LENGTH,
          label: m['admin.settings.customization.home.bannerLabel'](),
          help: m['admin.settings.customization.home.bannerHint']()
        }}
      />
    </fieldset>

    <fieldset class="mt-8! p-0 border-0">
      <legend class="fr-h4">{m['admin.settings.customization.colors.title']()}</legend>
      <p class="fr-hint-text mt-0!">{m['admin.settings.customization.colors.hint']()}</p>
      <div class="gap-x-6 md:grid-cols-2 grid">
        {#each COLORS as { id, label } (id)}
          <FormColorInput
            {id}
            {label}
            help={m['admin.settings.customization.colors.fieldHint']()}
            errors={form.errors}
            bind:value={form.form[id]}
          />
        {/each}
      </div>
    </fieldset>

    <FormInput
      id="votes_objective"
      type="number"
      label={m['admin.settings.customization.votesObjective']()}
      errors={form.errors}
      bind:value={form.form.votes_objective}
    />

    <fieldset class="mt-8! p-0 border-0">
      <legend class="fr-h4">{m['admin.settings.customization.ranking.title']()}</legend>
      <FormInput
        id="ranking_min_votes"
        type="number"
        required
        label={m['admin.settings.customization.ranking.minVotes']()}
        help={m['admin.settings.customization.ranking.minVotesHelp']()}
        errors={form.errors}
        bind:value={form.form.ranking_min_votes}
      />
      <FormInput
        id="ranking_max_rank_spread"
        type="number"
        required
        label={m['admin.settings.customization.ranking.maxRankSpread']()}
        help={m['admin.settings.customization.ranking.maxRankSpreadHelp']()}
        errors={form.errors}
        bind:value={form.form.ranking_max_rank_spread}
      />
    </fieldset>
  </Form>
</PageLayout>
