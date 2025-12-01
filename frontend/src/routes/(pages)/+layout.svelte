<script lang="ts">
  import { page } from '$app/state'
  import { Link } from '$components/dsfr'
  import Footer from '$components/Footer.svelte'
  import { Header, VoteGauge } from '$components/header'
  import { m } from '$lib/i18n/messages'

  let { children } = $props()

  const isHome = $derived(page.url.pathname === '/')
</script>

<Header hideDiscussBtn={isHome} />

{#if isHome}
  <Link button href="/ranking" text={m['header.banner']()} cornered class="w-auto!" />
{/if}

<div
  class="fr-container--fluid flex h-[48px] items-center justify-center bg-light-grey drop-shadow-(--raised-shadow) lg:hidden"
>
  <VoteGauge id="mobile-vote-gauge" />
</div>

{@render children()}

<Footer />
