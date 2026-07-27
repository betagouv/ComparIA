<script lang="ts">
  import { resolve } from '$app/paths'
  import { Button, Checkbox, Input } from '$components/dsfr'
  import { renderInlineMarkdown } from '$components/markdown/inline'
  import Markdown from '$components/markdown/MarkdownCode.svelte'
  import MarkdownInline from '$components/markdown/MarkdownInline.svelte'
  import { m } from '$lib/i18n/messages'

  let {
    kind,
    title = '',
    introduction = '',
    checkboxLabel,
    buttonLabel = ''
  }: {
    kind: 'arena' | 'sign-in'
    title?: string
    introduction?: string
    checkboxLabel: string
    buttonLabel?: string
  } = $props()

  const legalLinks = $derived([
    { label: m['footer.links.tos'](), href: resolve('/modalites') },
    { label: m['footer.links.privacy'](), href: resolve('/donnees-personnelles') }
  ])
</script>

<aside
  class="fr-p-4w bg-[--background-contrast-grey]"
  aria-label={m['admin.legal.participation.preview']()}
>
  <p class="fr-text--sm fr-text--bold fr-mb-3v">{m['admin.legal.participation.preview']()}</p>
  <div class="fr-card fr-card--shadow fr-p-4w bg-white">
    {#if kind === 'arena'}
      <h3 class="fr-h4 text-primary!">
        <MarkdownInline message={title || m['admin.legal.participation.modalTitle']()} />
      </h3>
      <div class="fr-text--sm">
        <Markdown
          message={introduction || m['admin.legal.participation.introductionPlaceholder']()}
          sanitize_html
        />
      </div>
    {:else}
      <h3 class="fr-h4 text-primary!">{m['auth.modal.email.title']()}</h3>
      <Input id="preview-email" label="Email" value="personne@exemple.fr" disabled />
    {/if}

    <Checkbox
      id={`preview-${kind}-consent`}
      checked={true}
      disabled
      label={renderInlineMarkdown(
        checkboxLabel || m['admin.legal.participation.checkboxPlaceholder']()
      )}
      links={legalLinks}
      linksClass="bg-none! no-underline!"
    />

    {#if kind === 'arena'}
      <div class="flex justify-end">
        <Button type="button" disabled>
          <MarkdownInline
            message={buttonLabel || m['admin.legal.participation.buttonPlaceholder']()}
            allowLinks={false}
          />
        </Button>
      </div>
    {:else}
      <Button type="button" text={m['auth.modal.email.submit']()} disabled class="w-full!" />
    {/if}
  </div>
</aside>
