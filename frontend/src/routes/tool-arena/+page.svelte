<script lang="ts">
  import { api } from '$lib/fastapi-client'
  import { ToolArenaForm, ToolResultCard, ToolRevealCard, ToolVoteArea } from './components'

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

  const bothFailed = $derived(!!errorA && !!errorB && !resultA && !resultB)

  async function handleCompare(task: string, goal: string) {
    phase = 'loading'
    compareError = null

    try {
      const data = await api.request<CompareResponse>('/tool-arena/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task, goal })
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

<div class="fr-container py-8">
  <h1 class="fr-h3 text-center mb-6">Tool Arena</h1>
  <p class="text-center text-grey mb-8">Compare two MCP tools on the same task</p>

  {#if phase === 'input'}
    {#if compareError}
      <div class="mb-6 rounded bg-red-50 border border-red-200 p-4 text-center">
        <p class="text-sm text-red-700 mb-0!">Error: {compareError}</p>
      </div>
    {/if}
    <ToolArenaForm onsubmit={handleCompare} />

  {:else if phase === 'loading'}
    <div class="text-center py-20">
      <p class="text-lg text-grey animate-pulse">Comparing tools...</p>
      <p class="text-sm text-grey mt-2">This may take up to 30 seconds</p>
    </div>

  {:else if phase === 'results'}
    <div class="gap-10 md:grid-cols-2 md:gap-6 grid mb-8">
      <ToolResultCard label="A" result={resultA} error={errorA} />
      <ToolResultCard label="B" result={resultB} error={errorB} />
    </div>

    {#if bothFailed}
      <div class="text-center">
        <p class="text-red-600 mb-4">Both tools encountered errors.</p>
        <button
          onclick={() => (phase = 'input')}
          class="px-6 py-3 rounded-lg border border-grey text-grey hover:bg-light-grey transition-colors"
        >
          Try Again
        </button>
      </div>
    {:else}
      <ToolVoteArea onvote={handleVote} />
    {/if}

  {:else if phase === 'revealed'}
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
      <p class="text-center text-grey mb-4">You voted: Tie</p>
    {/if}
    <div class="text-center mt-6">
      <button
        onclick={resetArena}
        class="px-6 py-3 rounded-lg border border-primary text-primary font-bold hover:bg-primary hover:text-white transition-colors"
      >
        New Comparison
      </button>
    </div>
  {/if}
</div>
