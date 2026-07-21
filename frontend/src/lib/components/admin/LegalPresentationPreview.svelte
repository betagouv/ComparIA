<script lang="ts">
  import { Button, Checkbox, Input } from '$components/dsfr'
  import Markdown from '$components/markdown/MarkdownCode.svelte'
  import MarkdownInline from '$components/markdown/MarkdownInline.svelte'
  import { renderInlineMarkdown } from '$components/markdown/inline'
  import { CANONICAL_LEGAL_LINKS } from '$lib/consent'

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
</script>

<aside class="fr-p-4w bg-[--background-contrast-grey]" aria-label="Aperçu utilisateur">
  <p class="fr-text--sm fr-text--bold fr-mb-3v">Aperçu utilisateur</p>
  <div class="fr-card fr-card--shadow fr-p-4w bg-white">
    {#if kind === 'arena'}
      <h3 class="fr-h4 text-primary!">
        <MarkdownInline message={title || 'Titre de la fenêtre'} />
      </h3>
      <div class="fr-text--sm">
        <Markdown message={introduction || 'Le texte introductif apparaîtra ici.'} sanitize_html />
      </div>
    {:else}
      <h3 class="fr-h4 text-primary!">Se connecter ou s’inscrire</h3>
      <Input id="preview-email" label="Email" value="personne@exemple.fr" disabled />
    {/if}

    <Checkbox
      id={`preview-${kind}-consent`}
      checked={true}
      disabled
      label={renderInlineMarkdown(checkboxLabel || 'Le texte associé à la case apparaîtra ici.')}
      links={CANONICAL_LEGAL_LINKS}
      linksClass="bg-none! no-underline!"
    />

    {#if kind === 'arena'}
      <div class="flex justify-end">
        <Button type="button" disabled>
          <MarkdownInline message={buttonLabel || 'Continuer'} allowLinks={false} />
        </Button>
      </div>
    {:else}
      <Button type="button" text="Recevoir le code de connexion" disabled class="w-full!" />
    {/if}
  </div>
</aside>
