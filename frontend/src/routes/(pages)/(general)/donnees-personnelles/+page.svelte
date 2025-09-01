<script>
  import SeoHead from '$components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'
</script>

<SeoHead title={m['seo.titles.donnees-personnelles']()} />

<main class="lg:py-15 py-10">
  <div class="fr-container">
    <h1 id="politique-de-confidentialite">{m['general.privacy.title']()}</h1>
    <p>{m['general.privacy.desc']()}</p>

    <h2 id="cookies">{m['general.privacy.cookiesTitle']()}</h2>
    <p>{m['general.privacy.cookiesDesc']()}</p>
    <p>{m['general.privacy.cookiesDescMore']()}</p>

    <div id="matomo-opt-out"></div>
    <script
      src="https://stats.beta.gouv.fr/index.php?module=CoreAdminHome&action=optOutJS&divId=matomo-opt-out&language=auto&showIntro=1"
    ></script>

    <h2 id="cookie-banner">{m['general.privacy.cookiesBannerTitle']()}</h2>
    <p>{m['general.privacy.cookiesBannerDesc']()}</p>
    <p>{m['general.privacy.cookiesBannerNoNeed']()}</p>
    <p>
      {@html sanitize(
        m['general.privacy.cookiesBannerTools']({
          matomoLinkProps: externalLinkProps('https://matomo.org/'),
          libreLinkProps: externalLinkProps('https://matomo.org/free-software/'),
          cnilLinkProps: externalLinkProps(
            'https://www.cnil.fr/fr/solutions-pour-la-mesure-daudience'
          )
        })
      )}
    </p>

    <h2 id="data-access">{m['general.privacy.dataAccessTitle']()}</h2>
    <p>
      {@html sanitize(
        m['general.privacy.dataAccessDesc']({
          linkProps: externalLinkProps(
            'https://stats.beta.gouv.fr/index.php?module=CoreHome&action=index&idSite=126&period=day&date=yesterday#?period=day&date=yesterday&category=Dashboard_Dashboard&subcategory=1&idSite=126'
          )
        })
      )}
    </p>
    <p>
      {@html sanitize(
        m['general.privacy.dataAccessDatasets']({
          linkProps: externalLinkProps('https://huggingface.co/ministere-culture')
        })
      )}
    </p>

    <h2 id="privacy">{m['general.privacy.privacyTitle']()}</h2>
    <p>{m['general.privacy.privacyDesc']()}</p>
    <p>{m['general.privacy.privacyData']()}</p>
    <ul>
      <li>{m['general.privacy.privacyDataArena']()}</li>
      <li>{m['general.privacy.privacyDataForm']()}</li>
    </ul>
    <p>
      {@html sanitize(m['general.privacy.privacyResp']({ linkProps: 'href="/modalites"' }))}
    </p>

    <h2 id="data-use">{m['general.privacy.dataUseTitle']()}</h2>
    <p>{m['general.privacy.dataUseDesc']()}</p>

    <h2 id="data-time">{m['general.privacy.dataTimeTitle']()}</h2>
    <p>{m['general.privacy.dataTimeDesc']()}</p>

    <h2 id="data-responsability">{m['general.privacy.dataRespTitle']()}</h2>
    <p>{m['general.privacy.dataRespDesc']()}</p>

    <h2 id="data-extra">{m['general.privacy.dataExtraTitle']()}</h2>
    <ul>
      <li>{m['general.privacy.dataExtraHost']()}</li>
      <li>{m['general.privacy.dataExtraCountry']()}</li>
      <li>{m['general.privacy.dataExtraWhat']()}</li>
      <li>
        {@html sanitize(
          m['general.privacy.dataExtraWarranty']({
            linkProps: externalLinkProps(
              'https://storage.gra.cloud.ovh.net/v1/AUTH_325716a587c64897acbef9a4a4726e38/contracts/9e74492-OVH_Data_Protection_Agreement-FR-6.0.pdf'
            )
          })
        )}
      </li>
    </ul>
  </div>
</main>
