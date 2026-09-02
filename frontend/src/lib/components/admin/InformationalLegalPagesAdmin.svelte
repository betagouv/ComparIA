<script lang="ts">
  import { Button, Checkbox, Input, Select, Textarea } from '$components/dsfr'
  import { api } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { onMount } from 'svelte'

  type PageKey = 'legal_notice' | 'accessibility' | 'ecodesign'
  type PageMode = 'internal' | 'external'
  type PageConfig = {
    mode: PageMode
    external_url: string | null
    visible_in_legal_menu: boolean
    visible_in_settings: boolean
    content_by_locale: Record<string, string>
  }
  type InformationalPages = { pages: Record<PageKey, PageConfig> }

  const pageKeys: PageKey[] = ['legal_notice', 'accessibility', 'ecodesign']
  const locales = [
    { value: 'fr', label: 'Français' },
    { value: 'en', label: 'English' }
  ]

  let loading = $state(true)
  let saving = $state(false)
  let selectedLocales = $state<Record<PageKey, string>>({
    legal_notice: 'fr',
    accessibility: 'fr',
    ecodesign: 'fr'
  })
  let errors = $state<Partial<Record<PageKey, string>>>({})
  let pages = $state<InformationalPages['pages']>()

  onMount(load)

  function pageTitle(key: PageKey) {
    return m[`admin.legal.informational.pages.${key}`]()
  }

  async function load() {
    loading = true
    try {
      const result = await api.request<InformationalPages>('/admin/legal/informational-pages')
      pages = result.pages
    } catch (error) {
      useToast((error as Error).message, 6000, 'error')
    } finally {
      loading = false
    }
  }

  function validate() {
    const nextErrors: Partial<Record<PageKey, string>> = {}
    if (!pages) return false
    for (const key of pageKeys) {
      const config = pages[key]
      if (config.mode !== 'external') continue
      try {
        const url = new URL(config.external_url ?? '')
        if (url.protocol !== 'https:' || url.username || url.password) throw new Error()
      } catch {
        nextErrors[key] = m['admin.legal.informational.externalUrlError']()
      }
    }
    errors = nextErrors
    return Object.keys(nextErrors).length === 0
  }

  async function save(event: SubmitEvent) {
    event.preventDefault()
    if (!pages || !validate()) return
    saving = true
    try {
      const result = await api.request<InformationalPages>('/admin/legal/informational-pages', {
        method: 'PUT',
        body: JSON.stringify({ pages })
      })
      pages = result.pages
      useToast(m['admin.legal.informational.saved'](), 4000)
    } catch (error) {
      useToast((error as Error).message, 6000, 'error')
    } finally {
      saving = false
    }
  }
</script>

{#if loading}
  <p role="status">{m['admin.legal.informational.loading']()}</p>
{:else if pages}
  <form onsubmit={save} class="max-w-[1000px]">
    {#each pageKeys as key (key)}
      {@const config = pages[key]}
      {@const locale = selectedLocales[key]}
      <fieldset class="fr-fieldset fr-mb-8v" aria-labelledby="{key}-title">
        <legend class="fr-fieldset__legend fr-h3" id="{key}-title">{pageTitle(key)}</legend>
        <div class="fr-fieldset__element">
          <fieldset class="fr-fieldset" aria-labelledby="{key}-mode-label">
            <legend class="fr-fieldset__legend fr-text--bold" id="{key}-mode-label">
              {m['admin.legal.informational.modeLabel']()}
            </legend>
            <div class="fr-fieldset__element fr-fieldset__element--inline">
              <div class="fr-radio-group">
                <input id="{key}-internal" type="radio" value="internal" bind:group={config.mode} />
                <label class="fr-label" for="{key}-internal">
                  {m['admin.legal.informational.internal']()}
                </label>
              </div>
            </div>
            <div class="fr-fieldset__element fr-fieldset__element--inline">
              <div class="fr-radio-group">
                <input id="{key}-external" type="radio" value="external" bind:group={config.mode} />
                <label class="fr-label" for="{key}-external">
                  {m['admin.legal.informational.external']()}
                </label>
              </div>
            </div>
          </fieldset>
        </div>

        {#if config.mode === 'external'}
          <div class="fr-fieldset__element">
            <Input
              id="{key}-external-url"
              type="url"
              label={m['admin.legal.informational.externalUrl']()}
              help={m['admin.legal.informational.externalUrlHelp']()}
              error={errors[key]}
              required
              value={config.external_url ?? ''}
              oninput={(event) => (config.external_url = event.currentTarget.value)}
            />
          </div>
        {:else}
          <div class="fr-fieldset__element">
            <Select
              id="{key}-locale"
              label={m['admin.legal.informational.locale']()}
              options={locales}
              bind:selected={selectedLocales[key]}
            />
            <Textarea
              id="{key}-content-{locale}"
              label={m['admin.legal.informational.contentLabel']({
                locale: locales.find((item) => item.value === locale)?.label ?? locale
              })}
              help={m['admin.legal.markdownHelp']()}
              rows={12}
              value={config.content_by_locale[locale] ?? ''}
              oninput={(event) => (config.content_by_locale[locale] = event.currentTarget.value)}
            />
          </div>
        {/if}

        <div class="fr-fieldset__element">
          <fieldset class="fr-fieldset" aria-labelledby="{key}-visibility-label">
            <legend class="fr-fieldset__legend fr-text--bold" id="{key}-visibility-label">
              {m['admin.legal.informational.visibilityLabel']()}
            </legend>
            <div class="fr-fieldset__element">
              <Checkbox
                id="{key}-visible-legal-menu"
                label={m['admin.legal.informational.visibleInLegalMenu']()}
                bind:checked={config.visible_in_legal_menu}
              />
            </div>
            <div class="fr-fieldset__element">
              <Checkbox
                id="{key}-visible-settings"
                label={m['admin.legal.informational.visibleInSettings']()}
                bind:checked={config.visible_in_settings}
              />
            </div>
          </fieldset>
        </div>
      </fieldset>
    {/each}

    <div class="flex justify-end">
      <Button
        type="submit"
        text={saving
          ? m['admin.legal.informational.saving']()
          : m['admin.legal.informational.save']()}
        disabled={saving}
      />
    </div>
  </form>
{/if}
