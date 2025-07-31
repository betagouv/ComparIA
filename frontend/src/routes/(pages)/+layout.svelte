<script lang="ts">
  import { page } from '$app/state'
  import Header from '$lib/components/header/Header.svelte'
  import VoteGauge from '$lib/components/header/VoteGauge.svelte'

  let { children } = $props()
</script>

<Header />

{#if page.url.pathname === '/'}
  <div>
    <a class="temp-banner text-center" href="/datasets">
      Découvrez l’étude de Bunka.ai qui explore les questions posées sur compar:IA !
    </a>
  </div>
{/if}

<div class="fr-container--fluid gauge-banner flex items-center justify-center lg:hidden">
  <VoteGauge />
</div>

{@render children()}

<style>
  .gauge-banner {
    gap: 1em;
    height: 48px;
    background-color: #f3f5f9;
    --shadow-color: rgba(0, 0, 18, 0.16);
    --raised-shadow: 0 1px 3px var(--shadow-color);
    filter: drop-shadow(0 1px 3px var(--shadow-color));
  }

  a.temp-banner,
  a.temp-banner:hover,
  a.temp-banner:active {
    display: block;
    background-color: #6a6af4 !important;
    color: white !important;
    line-height: 1.5em;
    padding-top: 0.5em;
    padding-bottom: 0.5em;
    --underline-img: none;
  }
</style>
