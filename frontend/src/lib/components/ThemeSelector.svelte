<script lang="ts">
  import lightPictoSrc from '@gouvfr/dsfr/dist/artwork/pictograms/environment/sun.svg?no-inline'
  import darkPictoSrc from '@gouvfr/dsfr/dist/artwork/pictograms/environment/moon.svg?no-inline'
  import systemPictoSrc from '@gouvfr/dsfr/dist/artwork/pictograms/system/system.svg?no-inline'
  import { m } from '$lib/i18n/messages'

  const options = [
    { value: 'light', label: m['components.theme.options.light'](), imgSrc: lightPictoSrc },
    { value: 'dark', label: m['components.theme.options.dark'](), imgSrc: darkPictoSrc },
    {
      value: 'system',
      label: m['components.theme.options.system'](),
      subLabel: m['components.theme.options.systemSub'](),
      imgSrc: systemPictoSrc
    }
  ]
</script>

<button
  aria-controls="footer-display"
  data-fr-opened="false"
  class="fr-icon-theme-fill fr-btn--icon-left fr-footer__bottom-link"
>
  {m['components.theme.title']()}
</button>

<dialog id="footer-display" aria-labelledby="footer-display-title" class="fr-modal">
  <div class="fr-container fr-container--fluid fr-container-md">
    <div class="fr-grid-row fr-grid-row--center">
      <div class="fr-col-12 fr-col-md-6 fr-col-lg-4">
        <div class="fr-modal__body">
          <div class="fr-modal__header">
            <button
              aria-controls="footer-display"
              title={m['closeModal']()}
              type="button"
              id="button-14"
              class="fr-btn--close fr-btn"
            >
              {m['words.close']()}
            </button>
          </div>
          <div class="fr-modal__content">
            <h2 id="footer-display-title" class="fr-modal__title">
              {m['components.theme.title']()}
            </h2>
            <div id="fr-display" class="fr-display">
              <fieldset
                class="fr-fieldset"
                id="display-fieldset"
                aria-labelledby="display-fieldset-legend display-fieldset-messages"
              >
                <legend
                  class="fr-fieldset__legend--regular fr-fieldset__legend"
                  id="display-fieldset-legend"
                >
                  {m['components.theme.legend']()}
                </legend>

                {#each options as option (option.value)}
                  <div class="fr-fieldset__element">
                    <div class="fr-radio-group fr-radio-rich">
                      <input
                        value={option.value}
                        type="radio"
                        id="fr-radios-theme-{option.value}"
                        name="fr-radios-theme"
                      />
                      <label class="fr-label" for="fr-radios-theme-{option.value}">
                        {option.label}
                        {#if option.subLabel}
                          <span class="fr-hint-text">{option.subLabel}</span>
                        {/if}
                      </label>
                      <div class="fr-radio-rich__pictogram">
                        <svg
                          aria-hidden="true"
                          class="fr-artwork"
                          viewBox="0 0 80 80"
                          width="80px"
                          height="80px"
                        >
                          <use
                            class="fr-artwork-decorative"
                            href={option.imgSrc + '#artwork-decorative'}
                          />
                          <use class="fr-artwork-minor" href={option.imgSrc + '#artwork-minor'} />
                          <use class="fr-artwork-major" href={option.imgSrc + '#artwork-major'} />
                        </svg>
                      </div>
                    </div>
                  </div>
                {/each}

                <div
                  class="fr-messages-group"
                  id="display-fieldset-messages"
                  aria-live="polite"
                ></div>
              </fieldset>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</dialog>
