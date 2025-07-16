<script lang="ts">
  import type { RevealData } from '$lib/chatService.svelte'
  import ModelInfoModal from '$lib/components/ModelInfoModal.svelte'

  let { data }: { data: RevealData } = $props()

  const { selected, modelsData, shareB64Data, ...infos } = data
</script>

<div id="reveal-screen" class="fr-pt-4w next-screen">
  <div>
    <div id="reveal-grid" class="grid-cols-md-2 fr-mx-md-12w grid grid-cols-1">
      {#each modelsData as { model, side, kwh, co2, tokens, lightbulb, lightbulbUnit, streaming, streamingUnit } (side)}
        <div class="rounded-tile fr-mb-1w fr-p-4w fr-mx-3v bg-white text-left">
          {#if selected === side}
            <span class="your-choice fr-mb-2w fr-mb-md-0">Votre vote</span>
          {/if}
          <h5 class="fr-mb-2w github-title">
            <img class="fr-mt-n2v relative inline" src="/orgs/{model.icon_path}" width="34" />
            {model.organisation}/<strong>{model.simple_name}</strong>
          </h5>
          <p class="fr-mb-2w">
            {#if model.fully_open_source}
              <span class="fr-badge fr-badge--green-emeraude fr-badge--no-icon fr-mr-1v fr-mb-1v">
                Open source
              </span>
            {:else if model.distribution === 'open-weights'}
              <span class="fr-badge fr-badge--yellow-tournesol fr-badge--no-icon fr-mr-1v fr-mb-1v">
                Semi-ouvert
              </span>
            {:else}
              <span
                class="fr-badge fr-badge--orange-terre-battue fr-badge--no-icon fr-mr-1v fr-mb-1v"
              >
                Propriétaire
              </span>
            {/if}
            <span class="fr-badge fr-badge--no-icon fr-badge--info fr-mr-1v fr-mb-1v">
              {#if model.distribution === 'open-weights'}
                {model.params} mds de paramètres
              {:else}
                Taille estimée ({model.friendly_size})
              {/if}
            </span>
            {#if model.release_date}
              <span class="fr-badge fr-badge--no-icon fr-mr-1v">
                Sortie {model.release_date}
              </span>
            {/if}
            <span class="fr-badge fr-badge--no-icon fr-mr-1v">
              Licence {#if model.distribution === 'open-weights'}{model.license}{:else}commerciale{/if}
            </span>
          </p>
          <p class="fr-mb-4w fr-text--sm text-grey-200">{model.excerpt}</p>
          <h6 class="fr-mb-2w">Impact énergétique de la discussion</h6>
          <!-- <p class="fr-mb-1v fr-text--xs text-grey">La taille du modèle et la longueur de ses réponses ont un impact
                    sur son
                    bilan.</p> -->
          <div class="energy-balance-1">
            <div class="rounded-tile fr-px-1w fr-py-1w relative text-center">
              <span
                class="fr-tooltip fr-placement"
                id="params-{side}"
                role="tooltip"
                aria-hidden="true"
              >
                Les paramètres ou les poids, comptés en milliards, sont les variables, apprises par
                un modèle au cours de son entrainement, qui déterminent ses réponses. Plus le nombre
                de paramètres est important, plus il est capable d’effectuer des tâches complexes.
              </span>
              <p>
                <a
                  class="fr-icon fr-icon--xs fr-icon-question-line"
                  aria-describedby="params-{side}"
                ></a>
              </p>

              <div class="">
                <p class="">
                  <strong>
                    <span class="fr-text--xxl">{model.params}</span>
                    <span class="fr-text--xs">
                      milliards param.
                      {#if model.distribution !== 'open-weights'}(est.){/if}
                      {#if model.quantization === 'q8'}(quantisé){/if}
                    </span>
                  </strong>
                </p>
                <p class="fr-text--sm">taille du modèle</p>
              </div>
            </div>
            <div class="self-center justify-self-center">
              <strong>×</strong>
            </div>
            <div class="rounded-tile fr-px-1w fr-py-1w relative text-center">
              <span
                class="fr-tooltip fr-placement"
                id="tokens-{side}"
                role="tooltip"
                aria-hidden="true"
              >
                L’IA analyse et génère des phrases à partir de mots ou de parties de mots d’à peu
                près quatre lettres, cette unité de texte est appelée token ("jeton"). Plus un texte
                est long, plus le nombre de tokens est grand.
              </span>
              <p>
                <a
                  class="fr-icon fr-icon--xs fr-icon-question-line"
                  aria-describedby="tokens-{side}"
                ></a>
              </p>
              <div class="">
                <p class="">
                  <strong>
                    <span class="fr-text--xxl">{tokens}</span>
                    <span class="fr-text--xs">tokens</span>
                  </strong>
                </p>
                <p class="fr-text--sm">taille du texte</p>
              </div>
            </div>

            <div class="self-center justify-self-center">
              <strong>=</strong>
            </div>
            <div class="rounded-tile with-icon fr-px-1w fr-py-1w relative">
              <span
                class="fr-tooltip fr-placement"
                id="energie-{side}"
                role="tooltip"
                aria-hidden="true"
              >
                Mesurée en wattheures, l’énergie consommée représente l'électricité utilisée par le
                modèle pour traiter une requête et générer la réponse correspondante. Plus un modèle
                est grand (en milliards de paramètres), plus il faut d'énergie pour produire un
                token.
              </span>
              <a class="fr-icon fr-icon--xs fr-icon-question-line" aria-describedby="energie-{side}"
              ></a>
              <div class="">
                <!-- flashlight -->
                <svg
                  transform="scale(1.33)"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  width="24"
                  height="24"
                  class=""
                >
                  <path fill="#0063cb" d="M13 10h7l-9 13v-9H4l9-13v9Z" />
                </svg>
              </div>
              <div class="">
                <!-- FIXME co2?? should be kwh? -->
                <p>
                  <strong>
                    <span class="fr-text--xxl">{co2.toFixed(co2 < 2 ? 2 : 0)}</span> Wh
                  </strong>
                </p>
                <p class="fr-text--xs">énergie conso.</p>
              </div>
            </div>
          </div>
          <h6 class="fr-mt-4w fr-mb-2w">Ce qui correspond à :</h6>
          <div class="energy-balance-2">
            <div class="rounded-tile with-icon fr-px-1w fr-py-1w relative">
              <span
                class="fr-tooltip fr-placement"
                id="co2-{side}"
                role="tooltip"
                aria-hidden="true"
              >
                Le CO<sub>2</sub> émis équivaut aux émissions de dioxyde de carbone produites par
                l’énergie utilisée pour faire fonctionner le modèle. Elle traduit l'impact
                environnemental lié à la consommation énergétique. Le calcul d’équivalence
                Wattheures/CO<sub>2</sub> diffère selon le mix énergétique de chaque pays. Or, les
                serveurs utilisés pour l’inférence des modèles ne sont pas tous localisés en France.
                Ainsi, le calcul d’équivalence repose sur la moyenne mondiale du taux d’émissions de
                CO<sub>2</sub> par énergie consommée.
              </span>

              <a class="fr-icon fr-icon--xs fr-icon-question-line" aria-describedby="co2-{side}"
              ></a>
              <div class="">
                <!-- cloud -->
                <svg
                  transform="scale(1.33)"
                  class=""
                  width="21"
                  height="17"
                  viewBox="0 0 21 17"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    fill-rule="evenodd"
                    clip-rule="evenodd"
                    d="M15.4556 16.5001H6.36473C3.70538 16.5016 1.43245 14.7449 0.984647 12.342C0.536847 9.93905 2.04472 7.59035 4.55382 6.78255C4.44169 4.63438 5.62808 2.60391 7.64094 1.49905C9.6538 0.394196 12.1666 0.394196 14.1794 1.49905C16.1923 2.60391 17.3787 4.63438 17.2666 6.78255C19.7757 7.59035 21.2835 9.93905 20.8357 12.342C20.3879 14.7449 18.115 16.5016 15.4556 16.5001Z"
                    fill="#CFCFCF"
                  />
                </svg>
              </div>
              <div class="">
                <p>
                  <strong>
                    <span class="fr-text--xxl">{co2.toFixed(co2 < 2 ? 2 : 0)}</span> g
                  </strong>
                </p>
                <p class="fr-text--xs">CO<sub>2</sub> émis</p>
              </div>
            </div>
            <div class="rounded-tile with-icon fr-px-1w fr-py-1w relative">
              <span
                class="fr-tooltip fr-placement"
                id="ampoule-{side}"
                role="tooltip"
                aria-hidden="true"
              >
                Donnée calculée sur la base de consommation d’une ampoule LED standard de 5W (E14)
              </span>
              <a class="fr-icon fr-icon--xs fr-icon-question-line" aria-describedby="ampoule-{side}"
              ></a>
              <div class="">
                <!-- lightbulb -->
                <svg
                  transform="scale(1.33)"
                  class=""
                  width="14"
                  height="19"
                  viewBox="0 0 14 19"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    fill-rule="evenodd"
                    clip-rule="evenodd"
                    d="M6.16953 14H3.62036C3.37286 12.9391 2.2562 12.0716 1.79786 11.5C-0.384161 8.77374 -0.0927751 4.82569 2.46585 2.44933C5.02447 0.0729714 8.98325 0.0736052 11.5411 2.45078C14.099 4.82796 14.3891 8.7761 12.2062 11.5016C11.7479 12.0725 10.6329 12.94 10.3854 14H7.83619V9.83331H6.16953V14ZM10.3362 15.6666V16.5C10.3362 17.4205 9.59 18.1666 8.66953 18.1666H5.33619C4.41572 18.1666 3.66953 17.4205 3.66953 16.5V15.6666H10.3362Z"
                    fill="#EFCB3A"
                  />
                </svg>
              </div>
              <div class="">
                <p>
                  <strong><span class="fr-text--xxl">{lightbulb}</span>{lightbulbUnit}</strong>
                </p>
                <p class="fr-text--xs">ampoule LED</p>
              </div>
            </div>
            <div class="rounded-tile with-icon fr-px-1w fr-py-1w relative">
              <a class="fr-icon fr-icon--xs fr-icon-question-line" aria-describedby="videos-{side}"
              ></a>
              <span
                class="fr-tooltip fr-placement"
                id="videos-{side}"
                role="tooltip"
                aria-hidden="true"
              >
                Donnée calculée selon l’impact carbone d’une heure de vidéo en ligne en haute
                définition, sur une télévision, en connexion wifi (source <a
                  href="https://impactco2.fr/outils/usagenumerique/streamingvideo"
                  rel="noopener external"
                  target="_blank">ADEME</a
                >)
              </span>
              <div class="">
                <!-- youtube -->
                <svg
                  transform="scale(1.33)"
                  width="20"
                  height="20"
                  viewBox="0 0 20 20"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M1.66406 3.32783C1.66406 2.87063 2.04349 2.5 2.49056 2.5H17.5042C17.9607 2.5 18.3307 2.87079 18.3307 3.32783V16.6722C18.3307 17.1293 17.9513 17.5 17.5042 17.5H2.49056C2.0341 17.5 1.66406 17.1292 1.66406 16.6722V3.32783ZM8.84898 7.01216C8.79423 6.97565 8.72989 6.95617 8.66406 6.95617C8.47998 6.95617 8.33073 7.10541 8.33073 7.28951V12.7105C8.33073 12.7763 8.35023 12.8407 8.38673 12.8954C8.48881 13.0486 8.69581 13.09 8.84898 12.9878L12.9147 10.2773C12.9513 10.2529 12.9827 10.2215 13.0071 10.1849C13.1093 10.0317 13.0679 9.82475 12.9147 9.72267L8.84898 7.01216Z"
                    fill="#F95A5C"
                  />
                </svg>
              </div>
              <div class="">
                <p>
                  <strong><span class="fr-text--xxl">{streaming}</span>{streamingUnit}</strong>
                </p>
                <p class="fr-text--xs">vidéos en ligne</p>
              </div>
            </div>
          </div>
          <div class="fr-grid-row fr-grid-row--center fr-mt-4w">
            <button
              class="fr-btn--sm grey-btn"
              data-fr-opened="false"
              aria-controls="fr-modal-{model.id}"
            >
              Voir plus
            </button>
          </div>
        </div>

        <ModelInfoModal {model} {infos} />
      {/each}
    </div>
  </div>
</div>
