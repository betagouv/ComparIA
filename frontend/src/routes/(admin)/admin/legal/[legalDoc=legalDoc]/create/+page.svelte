<script lang="ts">
  import { goto, invalidate } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { Badge, Button, Input, Select, Textarea } from '$components/dsfr'
  import { MarkdownCode as Markdown } from '$components/markdown'
  import { tryGetAuthContext } from '$lib/authContext.svelte'
  import { api } from '$lib/fastapi-client'
  import type { PublishLegalDocumentBody } from '$lib/generated/admin'
  import type { LegalDocumentKeys } from '$lib/generated/constants'
  import { getLocales } from '$lib/global.svelte'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import type { PageProps } from './$types'

  const { data, params }: PageProps = $props()

  const kind = $derived(params.legalDoc as LegalDocumentKeys)

  // The locales the instance serves, so a document can be published in each.
  const auth = tryGetAuthContext()
  const localeOptions = getLocales(auth?.config.enabled_locales).map((item) => ({
    value: item.code,
    label: item.long
  }))
  let publishing = $state(false)
  let reviewing = $state(false)
  let version = $state('')
  let locale = $state(auth?.config.default_locale ?? 'fr')
  let content = $state(data.documents.current?.content ?? '')
  let effectiveAt = $state('')
  let confirmed = $state(false)

  async function publish(e: SubmitEvent) {
    e.preventDefault()
    if (!confirmed) return
    publishing = true
    try {
      const body: PublishLegalDocumentBody = {
        version,
        locale,
        content,
        effective_at: effectiveAt ? new Date(effectiveAt).toISOString() : null,
        confirm_publication: true
      }
      await api.request(`/admin/legal/documents/${kind}`, {
        method: 'POST',
        body: JSON.stringify(body)
      })
      useToast(m['admin.legal.document.published'](), 4000)
      await invalidate('admin:legal')
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      publishing = false
    }
  }
</script>

<form onsubmit={publish} aria-labelledby="legal-document-draft-title">
  <Badge variant="yellow" size="sm" text={m['admin.legal.document.unpublished']()} />
  <div class="gap-4 md:flex-row md:items-start md:justify-between flex flex-col">
    <h2 id="legal-document-draft-title" class="fr-h3 fr-mt-2v fr-mb-1v">
      {m[`admin.legal.${kind}.draftTitle`]()}
    </h2>
    <Button
      variant="secondary"
      text={m['admin.legal.document.leave']()}
      onclick={() => goto(resolve(`/admin/legal/${kind}`))}
    />
  </div>

  <div class="fr-stepper fr-mb-6v max-w-[800px]">
    <h3 class="fr-stepper__title">
      {reviewing ? m['admin.legal.document.stepReview']() : m['admin.legal.document.stepWrite']()}
      <span class="fr-stepper__state">
        {m['admin.legal.document.stepState']({ current: reviewing ? 2 : 1 })}
      </span>
    </h3>
    <div class="fr-stepper__steps" data-fr-current-step={reviewing ? 2 : 1} data-fr-steps="2"></div>
    {#if !reviewing}
      <p class="fr-stepper__details">
        <span class="fr-text--bold">{m['admin.legal.document.nextStep']()}</span>
        {m['admin.legal.document.stepReview']()}
      </p>
    {/if}
  </div>

  {#if !reviewing}
    <div class="fr-grid-row fr-grid-row--gutters">
      <div class="fr-col-12 fr-col-lg-7">
        <Textarea
          id="legal-document-content"
          label={m[`admin.legal.${kind}.contentLabel`]()}
          help={m['admin.legal.markdownHelp']()}
          rows={24}
          maxlength={100000}
          required
          bind:value={content}
        />
      </div>
      <aside class="fr-col-12 fr-col-lg-5" aria-label={m['admin.legal.document.preview']()}>
        <p class="fr-label fr-mb-2v">{m['admin.legal.document.preview']()}</p>
        <div class="fr-p-4w bg-[--background-contrast-grey]">
          {#if content.trim()}
            <Markdown message={content} sanitize_html header_links variant="document" />
          {:else}
            <p class="fr-text--sm">{m['admin.legal.document.previewEmpty']()}</p>
          {/if}
        </div>
      </aside>
    </div>
  {:else}
    <div class="fr-grid-row fr-grid-row--gutters">
      <div class="fr-col-12 fr-col-md-6">
        <Input
          id="legal-document-version"
          label={m['admin.legal.document.versionLabel']()}
          help={m['admin.legal.document.versionHelp']()}
          maxlength={64}
          required
          bind:value={version}
        />
      </div>
      <div class="fr-col-12 fr-col-md-6">
        <Select
          id="legal-document-locale"
          label={m['admin.legal.document.locale']()}
          reserveHintSpace
          options={localeOptions}
          bind:selected={locale}
        />
      </div>
    </div>
    <Input
      id="legal-document-effective-at"
      type="datetime-local"
      label={m['admin.legal.document.effectiveAt']()}
      help={m['admin.legal.document.effectiveAtHelp']()}
      groupClass="fr-mt-4v"
      bind:value={effectiveAt}
    />
    <div class="fr-checkbox-group fr-mt-6v">
      <input id="legal-document-confirmation" type="checkbox" bind:checked={confirmed} />
      <label class="fr-label" for="legal-document-confirmation">
        {m['admin.legal.document.confirm']()}
      </label>
    </div>
  {/if}

  <div class="gap-3 fr-mt-6v flex flex-wrap justify-between">
    <div>
      {#if reviewing}
        <Button
          variant="secondary"
          text={m['admin.legal.document.backToWriting']()}
          onclick={() => (reviewing = false)}
        />
      {/if}
    </div>
    {#if reviewing}
      <Button
        type="submit"
        text={publishing
          ? m['admin.legal.document.publishing']()
          : m['admin.legal.document.publish']()}
        disabled={publishing || !confirmed}
      />
    {:else}
      <Button
        text={m['admin.legal.document.continue']()}
        icon="arrow-right-line"
        iconPos="right"
        onclick={() => (reviewing = true)}
      />
    {/if}
  </div>
</form>
