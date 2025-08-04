<script lang="ts">
  import { page } from '$app/state'
  import { Link } from '$lib/components/dsfr'
  import Footer from '$lib/components/Footer.svelte'
  import { Header, VoteGauge } from '$lib/components/header'
  import { m } from '$lib/i18n/messages'

  let { children } = $props()

  const isHome = $derived(page.url.pathname === '/')
</script>

<Header hideDiscussBtn={isHome} />

{#if isHome}
  <Link button href="#european" text={m['header.banner']()} cornered class="w-auto!" />
{/if}

<div
  class="fr-container--fluid bg-light-grey drop-shadow-(--raised-shadow) flex h-[48px] items-center justify-center lg:hidden"
>
  <VoteGauge id="mobile-vote-gauge" />
</div>

{@render children()}

<Footer />
