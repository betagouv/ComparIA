<script lang="ts">
  let { small = true }: { small?: boolean } = $props()
</script>

<header id="main-header" class="fr-header lg:overflow-visible overflow-hidden">
  <div class="fr-header__body">
    <div class="fr-container">
      <div class={['fr-header__body-row', { 'lg:py-1!': small }]}>
        <div
          class={['fr-header__brand fr-enlarge-link', { 'lg:-translate-x-1/8 lg:scale-75': small }]}
        >
          <div class="fr-header__brand-top w-auto!">
            <div class="fr-header__logo">
              <p class="fr-logo">
                République<br />Française
              </p>
            </div>
          </div>
          <div
            class="fr-header__service mx-1! sm:mx-3! sm:w-auto md:px-3! flex w-1/2 grow items-center before:content-none!"
          >
            <img
              src="/orgs/comparia.png"
              aria-hidden="true"
              alt=""
              width="46"
              class="me-4 sm:block hidden h-max"
            />
            <div>
              <p class="fr-header__service-title mb-0! leading-normal!">
                <a href="/tool-arena" title="compar:RAG — Le comparateur de pipelines RAG">
                  compar:RAG
                </a>
              </p>
              <p
                class="fr-header__service-tagline mb-0! leading-normal! text-dark-grey md:text-[14px]! text-[10px]!"
              >
                Le comparateur de pipelines RAG
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</header>
