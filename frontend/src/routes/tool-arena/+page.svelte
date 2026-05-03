<script lang="ts">
  import { browser, dev } from '$app/environment'
  import { env as publicEnv } from '$env/dynamic/public'
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

  let phase = $state<'input' | 'loading' | 'results' | 'revealed' | 'unavailable'>('input')
  let sessionHash = $state<string | null>(null)
  let resultA = $state<string | null>(null)
  let resultB = $state<string | null>(null)
  let errorA = $state<string | null>(null)
  let errorB = $state<string | null>(null)
  let revealData = $state<ToolRevealResponse | null>(null)
  let compareError = $state<string | null>(null)
  let voteError = $state<string | null>(null)
  let voting = $state(false)

  let secondHeader = $state<HTMLElement | undefined>(undefined)
  let secondHeaderSize = $derived(secondHeader?.offsetHeight ?? 0)

  const bothFailed = $derived(!!errorA && !!errorB && !resultA && !resultB)

  async function handleCompare(task: string, goal: string, documentContent: string = '') {
    phase = 'loading'
    compareError = null

    // Phase 2: detect 503 tool_unavailable from the backend's readiness gate
    // before falling back to the generic api.request error path. We intercept
    // the raw fetch here so we can read the structured body without losing
    // status info to ``parseErrorResponse``.
    try {
      // Mirror getBackendUrl() in $lib/fastapi-client so 503 detection uses
      // the same origin as the rest of the app.
      const base = !browser
        ? publicEnv.PUBLIC_API_LOCAL_URL || publicEnv.PUBLIC_API_URL || 'http://localhost:8001'
        : dev || publicEnv.PUBLIC_API_DEV_MODE === 'true'
          ? 'http://localhost:8001'
          : publicEnv.PUBLIC_API_URL || window.location.origin || 'http://localhost:8001'
      const url = `${base}/tool-arena/compare`
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task, goal, document_content: documentContent })
      })

      if (response.status === 503) {
        const body = await response.json().catch(() => ({}))
        if (body?.error === 'tool_unavailable') {
          phase = 'unavailable'
          return
        }
      }

      if (!response.ok) {
        const text = await response.text()
        throw new Error(text || `HTTP ${response.status}`)
      }

      const data = (await response.json()) as CompareResponse
      sessionHash = data.session_hash
      api.setSessionHash(data.session_hash)
      resultA = data.result_a
      resultB = data.result_b
      errorA = data.error_a
      errorB = data.error_b
      phase = 'results'
    } catch (err) {
      compareError = (err as Error).message || m['toolArena.errorFallback']()
      phase = 'input'
    }
  }

  async function handleVote(chosen: 'a' | 'b' | 'tie') {
    if (voting) return
    voting = true
    voteError = null
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
      voteError = (err as Error).message || m['toolArena.errorFallback']()
    } finally {
      voting = false
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
    voteError = null
    voting = false
  }
</script>

<SeoHead title={m['seo.titles.tool-arena']()} />

<Header hideNavigation={phase !== 'input'} hideDiscussBtn hideVoteGauge small />

{#if phase === 'results' || phase === 'revealed'}
  <div
    bind:this={secondHeader}
    id="second-header"
    class="fr-container--fluid bg-light-grey top-0 py-3 md:py-4 sticky z-3 drop-shadow-[--raised-shadow]"
  >
    <div class="fr-container gap-3 md:flex-row flex flex-col items-center">
      <div class="gap-3 md:flex-row flex basis-2/3 flex-col items-center">
        <div class="bg-primary px-4 py-2 font-bold text-white rounded-[3.75rem] text-nowrap">
          {m['header.chatbot.step']()} {phase === 'results' ? 1 : 2}/2
        </div>
        <div class="md:text-left flex flex-col text-center">
          <strong class="text-dark-grey">
            {phase === 'results' ? m['toolArena.step1.title']() : m['toolArena.step2.title']()}
          </strong>
          <p class="mt-2! mb-0! text-sm! leading-normal! text-grey md:mt-0!">
            {phase === 'results' ? m['toolArena.step1.desc']() : m['toolArena.step2.desc']()}
          </p>
        </div>
      </div>
      {#if phase === 'revealed'}
        <div class="md:block hidden w-full basis-1/3 items-center text-right">
          <button
            onclick={resetArena}
            class="fr-btn fr-btn--secondary fr-btn--icon-left fr-icon-edit-line"
          >
            {m['toolArena.newComparison']()}
          </button>
        </div>
      {/if}
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
          {m['toolArena.form.title']()}
        </h2>

        {#if compareError}
          <div class="mb-6 mt-4 cg-border rounded-lg! bg-white p-4 text-center">
            <p class="fr-text--sm text-red-600 mb-0!">{compareError}</p>
          </div>
        {/if}

        <ToolArenaForm onsubmit={handleCompare} />
      </div>
    </div>

  {:else if phase === 'unavailable'}
    <div class="fr-container py-10 md:py-24">
      <div class="fr-col-xl-8 m-auto text-center">
        <h2 class="mb-4!" style="font-size: clamp(1.5rem, 2.5vw, 2rem); font-weight: 700;">
          {m['toolArena.unavailable.title']()}
        </h2>
        <p class="fr-text--sm text-grey mb-6">{m['toolArena.unavailable.message']()}</p>
        <Button onclick={resetArena}>{m['toolArena.tryAgain']()}</Button>
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
          <p class="fr-text--sm text-red-600 mb-4">{m['toolArena.bothToolsFailed']()}</p>
          <Button onclick={resetArena}>{m['toolArena.tryAgain']()}</Button>
        </div>
      {:else}
        <ToolVoteArea onvote={handleVote} />
        {#if voteError}
          <div class="text-center py-4 mt-2">
            <p class="fr-text--sm text-red-600 mb-2">{voteError}</p>
            <Button onclick={resetArena}>{m['toolArena.tryAgain']()}</Button>
          </div>
        {/if}
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
