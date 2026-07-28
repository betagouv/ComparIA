<script lang="ts">
  import { m } from '$lib/i18n/messages'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'
</script>

<!-- Served until a privacy policy is published from the backoffice. -->
<div>
  <p>{m['general.privacy.desc']()}</p>

  <h2 id="cookies">{m['general.privacy.cookiesTitle']()}</h2>
  <p>{m['general.privacy.cookiesDesc']()}</p>
  <p>{m['general.privacy.cookiesDescMore']()}</p>

  <div id="matomo-opt-out"></div>

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

  <h2 id="tally">{m['general.privacy.tallyTitle']()}</h2>
  <p>
    {@html sanitize(
      m['general.privacy.tallyDesc']({
        tallyLinkProps: externalLinkProps('https://tally.so/')
      })
    )}
  </p>
  <ul>
    <li>{m['general.privacy.tallyNewsletter']()}</li>
    <li>{m['general.privacy.tallyFeedback']()}</li>
  </ul>
  <p>
    {@html sanitize(
      m['general.privacy.tallyData']({
        tallyPrivacyLinkProps: externalLinkProps('https://tally.so/help/privacy-policy')
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
    {@html sanitize(m['general.privacy.privacyResp']({ linkProps: 'href="/arene/modalites"' }))}
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

  <script
    src="https://stats.beta.gouv.fr/index.php?module=CoreAdminHome&action=optOutJS&divId=matomo-opt-out&language=auto&showIntro=1"
  ></script>
</div>
