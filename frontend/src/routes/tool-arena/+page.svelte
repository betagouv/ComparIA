<script lang="ts">
  import { api } from '$lib/fastapi-client'
  import { ToolArenaForm, ToolResultCard, ToolRevealCard, ToolVoteArea } from './components'
  import { Button } from '$components/dsfr'
  import Header from '$components/header/Header.svelte'
  import SeoHead from '$components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'

  type CompareResponse = {
    session_hash: string
    result_a: string | null
    result_b: string | null
    error_a: string | null
    error_b: string | null
  }

  type ToolRevealInfo = {
    pos: string
    name: string
    description: string
    duration_ms: number
    error: string | null
  }

  type ToolRevealResponse = {
    chosen: string
    tool_a: ToolRevealInfo
    tool_b: ToolRevealInfo
  }

  let phase = $state<'input' | 'loading' | 'results' | 'revealed'>('input')
  let sessionHash = $state<string | null>(null)
  let resultA = $state<string | null>(null)
  let resultB = $state<string | null>(null)
  let errorA = $state<string | null>(null)
  let errorB = $state<string | null>(null)
  let revealData = $state<ToolRevealResponse | null>(null)
  let compareError = $state<string | null>(null)

  let secondHeader = $state<HTMLElement | undefined>(undefined)
  let secondHeaderSize = $derived(secondHeader?.offsetHeight ?? 0)

  const bothFailed = $derived(!!errorA && !!errorB && !resultA && !resultB)

  async function handleCompare(task: string, goal: string, documentContent: string = '') {
    phase = 'loading'
    compareError = null

    try {
      const data = await api.request<CompareResponse>('/tool-arena/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task, goal, document_content: documentContent })
      })

      sessionHash = data.session_hash
      api.setSessionHash(data.session_hash)
      resultA = data.result_a
      resultB = data.result_b
      errorA = data.error_a
      errorB = data.error_b
      phase = 'results'
    } catch (err) {
      compareError = (err as Error).message || 'An unexpected error occurred'
      phase = 'input'
    }
  }

  async function handleVote(chosen: 'a' | 'b' | 'tie') {
    try {
      const data = await api.request<ToolRevealResponse>('/tool-arena/vote', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-Hash': sessionHash!
        },
        body: JSON.stringify({ chosen })
      })
      revealData = data
      phase = 'revealed'
    } catch (err) {
      console.error('Vote failed:', err)
    }
  }

  function resetArena() {
    phase = 'input'
    sessionHash = null
    resultA = null
    resultB = null
    errorA = null
    errorB = null
    revealData = null
    compareError = null
  }
</script>

<SeoHead title={m['seo.titles.tool-arena']()} />

<Header hideNavigation={phase !== 'input'} hideDiscussBtn hideVoteGauge small />

{#if phase === 'results' || phase === 'revealed'}
  <div
    bind:this={secondHeader}
    class="fr-container--fluid bg-light-grey sticky z-3 top-0"
  >
    <div class="fr-container">
      <div class="py-3 flex items-center justify-between">
        <div class="flex items-center gap-4">
          <div class="flex items-center gap-2">
            <div class="c-bot-disk-a"></div>
            <span class="font-medium fr-text--sm">
              {phase === 'revealed' ? revealData!.tool_a.name : 'Tool A'}
            </span>
          </div>
          <span class="text-grey">vs</span>
          <div class="flex items-center gap-2">
            <div class="c-bot-disk-b"></div>
            <span class="font-medium fr-text--sm">
              {phase === 'revealed' ? revealData!.tool_b.name : 'Tool B'}
            </span>
          </div>
        </div>
        {#if phase === 'results'}
          <span class="fr-text--sm text-grey">{m['toolArena.step1.desc']()}</span>
        {/if}
      </div>
    </div>
  </div>
{/if}

<div class="fr-container pt-4 pb-0 flex justify-end">
  <a href="/tool-arena/leaderboard" class="fr-link fr-text--sm">
    {m['toolArena.reveal.thanks.cta']()} &rarr;
  </a>
</div>

<main class="bg-very-light-grey relative min-h-screen" style="--second-header-size: {secondHeaderSize}px;">
  {#if phase === 'input'}
    <div id="prompt-area" class="fr-container py-10 md:py-24">
      <div class="fr-col-xl-8 m-auto">
        <h2 class="mb-0! text-center" style="font-size: clamp(1.75rem, 3vw, 2.5rem); font-weight: 700;">
          {m['toolArena.step1.title']()}
        </h2>

        {#if compareError}
          <div class="mb-6 mt-4 cg-border rounded-lg! bg-white p-4 text-center">
            <p class="fr-text--sm text-red-600 mb-0!">{compareError}</p>
          </div>
        {/if}

        <ToolArenaForm onsubmit={handleCompare} />
      </div>
    </div>

  {:else if phase === 'loading'}
    <div class="fr-container py-10 md:py-24">
      <div class="fr-col-xl-8 m-auto text-center">
        <h2 class="mb-4!" style="font-size: clamp(1.75rem, 3vw, 2.5rem); font-weight: 700;">
          {m['toolArena.loading.title']()}
        </h2>
        <div class="py-16">
          <div class="flex justify-center mb-6">
            <div class="flex gap-2">
              <div class="c-bot-disk-a animate-pulse"></div>
              <span class="text-grey animate-pulse">vs</span>
              <div class="c-bot-disk-b animate-pulse"></div>
            </div>
          </div>
          <p class="fr-text--sm text-grey">{m['toolArena.loading.subtitle']()}</p>
        </div>
      </div>
    </div>

  {:else if phase === 'results'}
    <div class="fr-container py-8 md:py-12">
      <div class="gap-10 md:grid-cols-2 md:gap-6 grid mb-8">
        <ToolResultCard label="A" result={resultA} error={errorA} />
        <ToolResultCard label="B" result={resultB} error={errorB} />
      </div>

      {#if bothFailed}
        <div class="text-center py-7">
          <p class="fr-text--sm text-red-600 mb-4">Both tools encountered errors.</p>
          <Button onclick={() => (phase = 'input')}>Try Again</Button>
        </div>
      {:else}
        <ToolVoteArea onvote={handleVote} />
      {/if}
    </div>

  {:else if phase === 'revealed'}
    <div class="fr-container py-8 md:py-12">
      <div class="gap-5 lg:grid-cols-2 lg:gap-6 grid grid-cols-1 mb-8">
        <ToolRevealCard
          {...revealData!.tool_a}
          selected={revealData!.chosen === 'a'}
        />
        <ToolRevealCard
          {...revealData!.tool_b}
          selected={revealData!.chosen === 'b'}
        />
      </div>
      {#if revealData!.chosen === 'tie'}
        <p class="fr-text--sm text-grey text-center mb-4">{m['vote.bothEqual']()}</p>
      {/if}
      <div class="text-center mt-8 mb-8">
        <p class="fr-text--sm text-grey mb-4">{m['toolArena.reveal.thanks.title']()}</p>
        <Button onclick={resetArena}>{m['toolArena.newComparison']()}</Button>
      </div>
    </div>
  {/if}
</main>
