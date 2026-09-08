<script lang="ts">
  import { resolve } from '$app/paths'
  import PageLayout from '$components/PageLayout.svelte'
  import { m } from '$lib/i18n/messages'
</script>

<PageLayout
  seoTitle={m['admin.legal.hub.title']()}
  title={m['admin.legal.hub.title']()}
  subtitle={m['admin.legal.hub.subtitle']()}
>
  <div class="max-w-[900px]">
    <section class="fr-mb-8v" aria-labelledby="participation-journey-group-title">
      <h2 id="participation-journey-group-title" class="fr-h5 fr-mb-2v">
        {m['admin.legal.hub.journeyGroup']()}
      </h2>
      <ul class="fr-raw-list">
        <li class="fr-py-3v">
          <h3 class="fr-h5 fr-mb-1v">
            <a
              class="fr-link fr-icon-arrow-right-line fr-link--icon-right bg-none! no-underline!"
              href={resolve('/admin/conditions-participation')}
            >
              {m['admin.legal.hub.journeyLink']()}
            </a>
          </h3>
          <p class="fr-text--sm fr-mb-0">{m['admin.legal.hub.journeyDescription']()}</p>
        </li>
      </ul>
    </section>

    <section aria-labelledby="legal-documents-group-title">
      <h2 id="legal-documents-group-title" class="fr-h5 fr-mb-2v">
        {m['admin.legal.hub.documentsGroup']()}
      </h2>
      <ul class="fr-raw-list">
        <li class="fr-py-3v">
          <h3 class="fr-h5 fr-mb-1v">
            <a
              class="fr-link fr-icon-arrow-right-line fr-link--icon-right bg-none! no-underline!"
              href={resolve('/admin/legal/conditions')}
            >
              {m['admin.legal.terms.title']()}
            </a>
          </h3>
          <p class="fr-text--sm fr-mb-0">{m['admin.legal.hub.termsDescription']()}</p>
        </li>
        <li class="fr-py-3v">
          <h3 class="fr-h5 fr-mb-1v">
            <a
              class="fr-link fr-icon-arrow-right-line fr-link--icon-right bg-none! no-underline!"
              href={resolve('/admin/legal/confidentialite')}
            >
              {m['admin.legal.privacy.title']()}
            </a>
          </h3>
          <p class="fr-text--sm fr-mb-0">{m['admin.legal.hub.privacyDescription']()}</p>
        </li>
        <li class="fr-py-3v">
          <h3 class="fr-h5 fr-mb-1v">
            <a
              class="fr-link fr-icon-arrow-right-line fr-link--icon-right bg-none! no-underline!"
              href={resolve('/admin/legal/pages-information')}
            >
              {m['admin.legal.informational.title']()}
            </a>
          </h3>
          <p class="fr-text--sm fr-mb-0">
            {m['admin.legal.hub.informationalDescription']()}
          </p>
        </li>
      </ul>
    </section>
  </div>
</PageLayout>
