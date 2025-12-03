<script>
  import { Icon, Link } from '$components/dsfr'
  import { getI18nContext } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'

  const locale = getLocale()
  const i18nData = getI18nContext()
</script>

<div class="grid gap-8 lg:grid-cols-2">
  <section class="cg-border cl-card">
    <h2 class="fr-h6">
      <Icon icon="government-line" size="lg" class="me-1 text-primary" />
      {m['product.partners.institution.title']()}
    </h2>

    {#if locale === 'fr' || locale === 'en'}
      <div class="cl-logos">
        <img
          src="/orgs/cnnum.png"
          alt="Conseil national du numérique"
          title="Conseil national du numérique"
          width="112px"
        />
        <img src="/orgs/etalab.svg" alt="Etalab" title="Etalab" width="240px" />
        <img
          src="/orgs/peren.svg"
          alt="PEReN, Pôle d'expertise de la régulation numérique"
          title="Pôle d'expertise de la régulation numérique (PEReN)"
          width="240px"
        />
      </div>
    {:else if locale === 'da'}
      <img
        src="/orgs/countries/da-light.png"
        alt={m['header.logoAlt']()}
        class="max-h-[75px] dark:hidden"
      />
      <img
        src="/orgs/countries/da-dark.png"
        alt={m['header.logoAlt']()}
        class="hidden max-h-[75px] dark:block"
      />
    {/if}
  </section>

  {#if locale === 'fr' || locale === 'en'}
    <section class="cg-border cl-card">
      <h2 class="fr-h6">
        <Icon icon="presentation" size="lg" class="me-1 text-yellow" />
        {m['product.partners.diffusion.title']()}
      </h2>

      <div class="cl-logos">
        <img src="/orgs/cafe-ia.png" alt="Cafés de l'IA" title="Cafés IA" width="104px" />
        <img
          src="/orgs/latitudes.png"
          alt="Latitudes"
          title="Latitudes"
          width="110px"
          class="dark:invert"
        />
        <img src="/orgs/pix.svg" alt="Pix" title="Pix" width="60px" />
        <img
          src="/orgs/fresque-de-lia.png"
          alt="Fresques de l'IA"
          title="Fresques de l'IA"
          width="94px"
          class="dark:invert"
        />
      </div>

      <p>{m['product.partners.diffusion.desc']()}</p>
      <p><strong>{m['product.partners.diffusion.catch']()}</strong></p>

      <Link
        button
        href="mailto:{i18nData.contact}"
        text={m['product.partners.diffusion.cta']()}
        class="w-full! sm:w-auto!"
      />
    </section>

    <section class="cg-border cl-card">
      <h2 class="fr-h6">
        <Icon icon="chat-search" size="lg" class="me-1 text-orange" />
        {m['product.partners.academy.title']()}
      </h2>

      <div class="cl-logos">
        <img src="/orgs/inria.png" alt="Inria" title="Inria" width="139px" />
      </div>

      <p>{m['product.partners.academy.desc']()}</p>
      <p><strong>{m['product.partners.academy.catch']()}</strong></p>

      <Link
        button
        href="mailto:{i18nData.contact}"
        text={m['actions.contactUs']()}
        class="w-full! sm:w-auto!"
      />
    </section>
  {/if}

  <section class="cg-border cl-card">
    <h2 class="fr-h6">
      <Icon icon="presentation" size="lg" class="me-1 text-green" />
      {m['product.partners.services.title']()}
    </h2>

    <div class="cl-logos">
      <img src="/orgs/impactco2.png" alt="Impact CO2" title="Impact CO2" width="123px" />
      <img src="/orgs/genai.png" alt="Gen AI Impact" title="Gen AI Impact" width="109px" />
    </div>

    <p>{m['product.partners.services.desc']()}</p>
  </section>
</div>

<style lang="postcss">
  @reference '$css/app.css';

  .cl-card {
    @apply bg-very-light-info p-4 md:p-8;
  }
  .cl-logos {
    @apply my-4 flex flex-wrap gap-8 *:object-contain;
  }
</style>
