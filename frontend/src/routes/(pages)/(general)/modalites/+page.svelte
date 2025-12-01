<script>
  import SeoHead from '$components/SEOHead.svelte'
  import { getI18nContext } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { getModelsContext } from '$lib/models'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'

  const i18nData = getI18nContext()
  const models = getModelsContext().models.filter((model) => model.status === 'enabled')
</script>

<SeoHead title={m['seo.titles.modalites']()} />

<main class="py-10 lg:py-15">
  <div class="fr-container">
    <h1 id="modalites-d-utilisation">{m['general.tos.title']()}</h1>

    <h2 id="1-champ-d-application">{m['general.tos.scopeTitle']()}</h2>
    <p>{m['general.tos.scopeDesc']()}</p>

    <h2 id="2-definitions">{m['general.tos.defsTitle']()}</h2>
    <p>{m['general.tos.defsUser']()}</p>
    <p>{m['general.tos.defsEditor']()}</p>
    <p>{m['general.tos.defsPlatform']()}</p>
    <p>{m['general.tos.defsModels']()}</p>
    <p>{m['general.tos.defsServices']()}</p>

    <h2 id="3-description-de-la-plateforme">{m['general.tos.descTitle']()}</h2>
    <p>{m['general.tos.descEditor']()}</p>

    <p>
      {@html sanitize(
        m['general.tos.descUse']({ linkProps: externalLinkProps('https://chat.lmsys.org/') })
      )}
    </p>
    <p>{m['general.tos.descDatasets']()}</p>

    <h2 id="4-fonctionnalites">{m['general.tos.featuresTitle']()}</h2>
    <p>{m['general.tos.featuresDesc']()}</p>
    <ul>
      <li>{m['general.tos.featuresDescMore']()}</li>
    </ul>
    <p>{m['general.tos.featuresModels']()}</p>
    <ul>
      <li>{m['general.tos.featuresModelsMore']()}</li>
    </ul>
    <p>{m['general.tos.featuresVote']()}</p>
    <ul>
      <li>{m['general.tos.featuresVoteMore']()}</li>
    </ul>
    <p>{m['general.tos.featuresDatasets']()}</p>
    <p>
      {@html sanitize(
        m['general.tos.featuresDatasetsMore']({
          linkProps: externalLinkProps('https://huggingface.co/ministere-culture')
        })
      )}
    </p>

    <h2 id="5-responsabilites">{m['general.tos.respTitle']()}</h2>
    <p>{m['general.tos.respUser']()}</p>
    <p>{m['general.tos.respLegal']()}</p>
    <p>{m['general.tos.respLegalMore']()}</p>
    <p>{m['general.tos.respPrivacy']()}</p>
    <p>{m['general.tos.respPrivacyMore']()}</p>
    <p>{m['general.tos.respEditor']()}</p>

    <h2 id="6-code-et-licences">{m['general.tos.licenceTitle']()}</h2>
    <p>
      {@html sanitize(
        m['general.tos.licenceCode']({
          linkProps: externalLinkProps('https://github.com/betagouv/languia')
        })
      )}
    </p>
    <p>{m['general.tos.licenceLLM']()}</p>

    <table class="fr-table fr-table__wrapper fr-table__container fr-table__content">
      <thead>
        <tr>
          <th>{m['general.tos.licenceLLMModel']()}</th>
          <th>{m['general.tos.licenceLLMNoticeLink']()}</th>
          <th>{m['general.tos.licenceLLMLicence']()}</th>
        </tr>
      </thead>
      <tbody>
        {#each models as model}
          <tr>
            <td>{model['simple_name']}</td>
            <td>
              {#if model.url}
                <a href={model.url} target="_blank" rel="noopener external">
                  {model.url}
                </a>
              {:else}
                {m['general.tos.licenceLLMUnavailable']()}
              {/if}
            </td>
            <td>{model['license']}</td>
          </tr>
        {/each}
      </tbody>
    </table>
    <p>{m['general.tos.licenceLLMEvolution']()}</p>

    <h2 id="7-disponibilite-des-services">{m['general.tos.dispoTitle']()}</h2>
    <p>{m['general.tos.dispoDesc']()}</p>
    <p>{m['general.tos.dispoRight']()}</p>
    <p>{m['general.tos.dispoWarranty']()}</p>
    <p>{m['general.tos.dispoResp']()}</p>

    <h2 id="8-evolution-des-modalites-d-utilisation">{m['general.tos.evoTitle']()}</h2>
    <p>{m['general.tos.evoDesc']()}</p>
    <p>{m['general.tos.evoDescMore']()}</p>

    <h2 id="9-contact">{m['general.tos.contactTitle']()}</h2>
    <p>
      {@html sanitize(
        m['general.tos.contactDesc']({
          linkProps: externalLinkProps(`mailto:${i18nData.contact}`),
          contactLink: i18nData.contact
        })
      )}
    </p>
  </div>
</main>
