<script lang="ts">
  import ThemeSelector from '$components/ThemeSelector.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'

  const locale = getLocale()

  const links = (
    [
      { href: '/mentions-legales', labelKey: 'legal' },
      { href: '/modalites', labelKey: 'tos' },
      { href: '/donnees-personnelles', labelKey: 'privacy' },
      { href: '/accessibilite', labelKey: 'accessibility' },
      { href: 'https://github.com/betagouv/languia', labelKey: 'sources' }
    ] as const
  ).map(({ href, labelKey }) => {
    return {
      href,
      label: m[`footer.links.${labelKey}`](),
      target: href.startsWith('http') ? '_blank' : undefined,
      rel: href.startsWith('http') ? 'noopener external' : undefined
    }
  })
</script>

<footer class="fr-footer fr-pb-2w" role="contentinfo" id="main-footer">
  <div class="fr-container">
    <div class="fr-footer__body">
      <div class="fr-footer__brand fr-enlarge-link">
        <a href="/" title={m['footer.backHome']()}>
          {#if locale === 'fr' || locale === 'en'}
            <p class="fr-logo">
              Ministère<br />de la culture
            </p>
          {:else if locale === 'da'}
            <img
              src={`/orgs/countries/da-light.png`}
              alt={m['header.logoAlt']()}
              class="max-h-[80px] dark:hidden"
            />
            <img
              src={`/orgs/countries/da-dark.png`}
              alt={m['header.logoAlt']()}
              class="hidden max-h-[80px] dark:block"
            />
          {:else}
            <img
              src={`/orgs/countries/${locale}.png`}
              alt={m['header.logoAlt']()}
              class="max-h-[100px]"
            />
          {/if}
        </a>
      </div>
      <div class="fr-footer__content">
        <p class="fr-footer__content-desc">
          <strong>{m['footer.helpUs']()}</strong><br />
          {@html sanitize(
            m['footer.writeUs']({
              linkProps: externalLinkProps('https://adtk8x51mbw.eu.typeform.com/to/duuGRyEX')
            })
          )}
        </p>
      </div>
    </div>
    <div class="fr-footer__bottom">
      <ul class="fr-footer__bottom-list">
        {#each links as { label, ...props }}
          <li class="fr-footer__bottom-item">
            <a class="fr-footer__bottom-link" {...props}>{label}</a>
          </li>
        {/each}
        <li class="fr-footer__bottom-item">
          <ThemeSelector />
        </li>
      </ul>
      <div class="fr-footer__bottom-copy">
        <p>
          {@html sanitize(
            m['footer.license.mention']({
              linkProps: externalLinkProps({
                href: 'https://github.com/etalab/licence-ouverte/blob/master/LO.md',
                title: m['footer.license.linkTitle']()
              })
            })
          )}
        </p>
      </div>
    </div>
  </div>
</footer>
