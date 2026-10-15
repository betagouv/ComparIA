<script lang="ts">
  import { goto } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import { Button, Icon, Toggle, Tooltip } from '$components/dsfr'
  import Pending from '$components/Pending.svelte'
  import TextPrompt from '$components/TextPrompt.svelte'
  import {
    getModeInfos,
    type APIModeAndPromptData,
    type PickRefusal
  } from '$lib/chatService.svelte'
  import { useLocalStorage } from '$lib/helpers/useLocalStorage.svelte'
  import { m } from '$lib/i18n/messages.js'
  import { getLimitsContext, type Spent } from '$lib/limits.svelte'
  import { getModelsContext } from '$lib/models'
  import type { SuggestionCategory } from '$lib/suggestions'
  import { sanitize } from '$lib/utils/commons'
  import { onMount, tick, untrack } from 'svelte'
  import { SvelteURLSearchParams } from 'svelte/reactivity'
  import GuidedPromptSuggestions from './GuidedPromptSuggestions.svelte'
  import MessageUser from './MessageUser.svelte'
  import ModelSelector from './ModelSelector.svelte'
  import { pausedModes } from './pausedModes'
  import PauseNotice from './PauseNotice.svelte'
  import PickPausedNotice, {
    pickPauseSaid,
    type PickPause,
    type TrimmedPause
  } from './PickPausedNotice.svelte'

  let {
    onPrompt,
    promptError,
    pause,
    pauseFromSend = false,
    pickRefusal,
    busyHint,
    loading,
    suggestions
  }: {
    onPrompt: (args: APIModeAndPromptData) => void | Promise<void>
    promptError?: string
    /** Set while an allowance is spent: the notice takes the place of the form. */
    pause?: Spent
    /** The pause met the prompt just sent, so it takes focus. */
    pauseFromSend?: boolean
    /** Set when the comparison asked for models the person may not use yet. */
    pickRefusal?: PickRefusal
    /** Set when the message just sent came with too many at once. */
    busyHint?: string
    loading: boolean
    suggestions: SuggestionCategory[]
  } = $props()

  let promptEl = $state<HTMLTextAreaElement>()

  const models = getModelsContext().models.filter((model) => model.status === 'enabled')
  const limits = getLimitsContext()

  let prompt = $state('')
  const mode = useLocalStorage<APIModeAndPromptData['mode']>('mode', 'random')
  const modelsSelection = useLocalStorage<string[]>('customModelsSelection', [], (parsed) => {
    if (Array.isArray(parsed) && parsed.every((item) => typeof item === 'string')) {
      const availableModelIds = new Set(models.map((llm) => llm.id))
      return parsed.filter((id) => availableModelIds.has(id))
    }
    return []
  })
  let webSearch = $state(false)
  let submitting = $state(false)
  // The refusal the person moved on from by changing the mode or the models.
  let dismissedRefusal = $state.raw<PickRefusal>()
  let toRandom = $state(false)
  // Paused models taken out of a saved or `?vs=` selection, until the person
  // changes the mode or the models.
  let trimmed = $state.raw<TrimmedPause>()

  function names(ids: string[]): string[] {
    return ids
      .map((id) => models.find((llm) => llm.id === id)?.name)
      .filter((name): name is string => !!name)
  }

  const modePauses = $derived(pausedModes(models, limits.paused))
  const modePause = $derived(mode.value === 'custom' ? undefined : modePauses.get(mode.value))
  const disabled = $derived(prompt == '' || !!promptError || loading || submitting || !!modePause)
  const shownRefusal = $derived(pickRefusal === dismissedRefusal ? undefined : pickRefusal)
  // Before anyone sends; a refusal, when there is one, already says it all.
  const pickPause = $derived.by((): PickPause | undefined => {
    if (shownRefusal) return undefined
    return modePause ? { kind: 'mode', ...modePause } : trimmed
  })
  // A refused send, told the same way and focused, since nothing started.
  const refusalPause = $derived.by((): PickPause | undefined => {
    if (!shownRefusal) return undefined
    const { detail, limit } = shownRefusal
    if (!limit.llm_ids?.length)
      return { kind: 'mode', until: limit.resets_at, full: detail === 'model_full_today' }
    return trimmedPause(limit.llm_ids, toRandom, shownRefusal)
  })

  /**
   * Models taken out of a pick, each told by its own reason: read from the
   * limits, and from the refusal that took them out until the limits are
   * read again.
   */
  function trimmedPause(ids: string[], toRandom: boolean, refusal?: PickRefusal): TrimmedPause {
    const isFull = (id: string) => {
      const reason = limits.paused.get(id)?.reason
      return reason ? reason === 'full' : refusal?.detail === 'model_full_today'
    }
    const told = refusal?.detail === 'expensive_allowance_spent' ? refusal.limit : limits.expensive
    return {
      kind: 'trimmed',
      full: names(ids.filter(isFull)),
      paused: names(ids.filter((id) => !isFull(id))),
      until: told?.resets_at ?? null,
      toRandom,
      network: told?.scope === 'network'
    }
  }

  /** Takes models out of the selection. A custom pick left empty goes random. */
  function takeOut(ids: string[]): boolean {
    modelsSelection.value = modelsSelection.value.filter((id) => !ids.includes(id))
    if (mode.value !== 'custom' || modelsSelection.value.length) return false
    mode.value = 'random'
    return true
  }
  const modeInfos = getModeInfos()
  const selectedMode = $derived(modeInfos.find((item) => item.value === mode.value)!)

  // A saved or `?vs=` choice may hold models paused since: take them out, and
  // say so in custom mode, where the person picked them. Not while sending:
  // a refused pick tells and takes out its own.
  $effect(() => {
    const out = modelsSelection.value.filter((id) => limits.paused.has(id))
    if (!out.length || submitting) return
    untrack(() => {
      const custom = mode.value === 'custom'
      const emptied = takeOut(out)
      if (custom) trimmed = trimmedPause(out, emptied)
    })
  })

  onMount(() => {
    const vsParam = page.url.searchParams.get('vs')
    if (!vsParam) return

    const humanIdToModel = new Map(models.map((llm) => [llm.human_id, llm.id!]))
    const validIds = [
      ...new Set(
        vsParam
          .split(',')
          .map((slug) => slug.trim())
          .map((slug) => humanIdToModel.get(slug))
          .filter((id): id is string => !!id)
      )
    ].slice(0, 2)

    if (validIds.length > 0) {
      mode.value = 'custom'
      modelsSelection.value = validIds
    } else {
      mode.value = 'random'
      modelsSelection.value = []
    }

    const params = new SvelteURLSearchParams(page.url.searchParams)
    params.delete('vs')
    const qs = params.toString()
    goto(qs ? resolve(`${page.url.pathname}?${qs}`) : page.url.pathname, { replaceState: true })
  })

  function selectPartialText(start?: number, end?: number): void {
    if (promptEl) {
      promptEl.focus()
      if (start !== undefined && end !== undefined) {
        promptEl.setSelectionRange(start, end)
        console.log(`[Textbox] Text selected from ${start} to ${end}`)
      } else {
        promptEl.select()
        console.log('[Textbox] All text selected')
      }
    } else {
      console.error("[Textbox] Element 'el' not found for selection.")
    }
  }

  async function onPromptSubmit() {
    if (loading || submitting) return

    submitting = true
    toRandom = false
    try {
      await onPrompt({
        mode: mode.value,
        custom_models_selection: modelsSelection.value,
        prompt_value: prompt,
        web_search: webSearch
      })
      // Take the refused models out, so sending again starts a comparison.
      const refused = pickRefusal?.limit.llm_ids
      if (refused?.length) toRandom = takeOut(refused)
    } finally {
      submitting = false
    }
  }

  // Changed by the person, not by onPromptSubmit: the refusal no longer fits.
  function setMode(value: APIModeAndPromptData['mode']) {
    mode.value = value
    dismissedRefusal = pickRefusal
    trimmed = undefined
  }

  function setModelsSelection(value: string[]) {
    modelsSelection.value = value
    dismissedRefusal = pickRefusal
    trimmed = undefined
  }

  function handlePromptSelected(
    text: string,
    selectionStart?: number,
    selectionEnd?: number
  ): void {
    prompt = text
    console.log(
      `[Index] handlePromptSelected: Received promptselected. Text: "${prompt}", Start: ${selectionStart}, End: ${selectionEnd}`
    )
    if (promptEl && selectionStart !== undefined && selectionEnd !== undefined) {
      const performSelection = () => {
        if (selectPartialText && typeof selectPartialText === 'function') {
          console.log(
            `[Index] Performing selection. Start: ${selectionStart}, End: ${selectionEnd}`
          )
          selectPartialText(selectionStart, selectionEnd)
        } else {
          console.warn(
            `[Index] Textbox element or selectPartialText method not available when trying to perform selection.`
          )
        }
      }

      // Select after Svelte tick and browser paint
      tick().then(() => {
        requestAnimationFrame(() => {
          performSelection()
        })
      })
    } else {
      // No valid selection range provided
      console.log(
        '[Index] handlePromptSelected: No specific selection range provided, or promptEl not ready. No text will be selected.',
        { text, selectionStart, selectionEnd }
      )
    }
  }
</script>

<!-- Present before loading starts so assistive technology announces the state change.
     It also tells a selection trimmed once the limits are read, after the page shows. -->
<p role="status" class="sr-only">
  {loading ? m['chatbot.loading']() : pickPause ? pickPauseSaid(pickPause) : ''}
</p>

{#if loading}
  <div id="prompt-area" class="fr-container px-4 py-2 md:px-6 md:py-5">
    <div class="gap-2 md:gap-5 flex flex-col">
      <div class="md:flex">
        <div
          class="cg-border md:me-3 rounded-lg! bg-white py-1 text-sm mb-3 md:mb-0 px-10 md:py-3 min-w-fit self-start border-dashed! text-center"
        >
          <Icon icon={selectedMode.icon} size="sm" class="text-primary" />
          <strong>{selectedMode.title}</strong>
          <Tooltip id="pending-mode-desc" text={selectedMode.description} size="xs" />
        </div>

        <MessageUser
          id="pending-user-message"
          message={{ content: prompt, user_content: prompt }}
        />
      </div>

      <Pending message={m['chatbot.loading']()} class="m-auto" aria-hidden="true" />
    </div>
  </div>
{:else}
  <div id="prompt-area" class="fr-container py-10 md:py-24 my-auto">
    <div class="fr-col-xl-8 m-auto">
      {#if pause}
        <!-- The card's title is the page's question then: "Comment puis-je vous
             aider ?" would invite typing above a card that says not yet. -->
        <div class="py-10">
          <PauseNotice {pause} focusTitle={pauseFromSend} level={2} />
        </div>
      {:else}
        <h2 class="fr-h4 mb-0! text-center">
          {m['arenaHome.title']()}
        </h2>
        <!-- Hidden until the limits are read: a pause would take its place. -->
        <div
          id="prompt-form"
          class={[
            'gap-3 py-10 md:grid-flow-row-dense md:grid-cols-6 grid',
            { 'cl-limits-pending invisible': !limits.read }
          ]}
        >
          <div class="md:order-none md:col-span-full order-1">
            <TextPrompt
              id="initial-prompt"
              bind:el={promptEl}
              bind:value={prompt}
              label={m['arenaHome.prompt.label']()}
              placeholder={m['arenaHome.prompt.placeholder']()}
              bind:error={promptError}
              hint={busyHint}
              disabled={loading}
              submitDisabled={disabled}
              hideLabel
              rows={4}
              onSubmit={() => onPromptSubmit()}
            />
          </div>

          <div class="gap-3 md:col-span-5 md:flex-row flex flex-col">
            <ModelSelector
              bind:mode={() => mode.value, setMode}
              bind:modelsSelection={() => modelsSelection.value, setModelsSelection}
              {models}
              disabled={loading}
              paused={limits.paused}
              expensive={limits.expensive}
              pausedModes={modePauses}
            />
            <Toggle
              id="web-search"
              bind:value={webSearch}
              checkedLabel={m['arenaHome.webSearch.enabled']()}
              uncheckedLabel={m['arenaHome.webSearch.disabled']()}
              hideCheckLabel
              labelPos="right"
              class="font-medium w-full! text-[14px]!"
              groupClass="grow my-auto"
            >
              {m['arenaHome.webSearch.label']()}
              <Tooltip id="web-search-tooltip" size="sm" class="ms-1">
                {@html sanitize(m['arenaHome.webSearch.tooltip']())}
              </Tooltip>
            </Toggle>
          </div>

          <Button
            type="submit"
            text={m['words.send']()}
            {disabled}
            class="md:w-auto! md:order-none order-2 h-full w-full! min-w-[130px] place-self-end"
            onclick={() => onPromptSubmit()}
          />

          <!-- After the send button in the DOM, and on screen too (RGAA 12.8). -->
          {#if refusalPause}
            <div class="md:col-span-full md:order-none order-3">
              <PickPausedNotice pause={refusalPause} focusOnShow />
            </div>
          {:else if pickPause}
            <div class="md:col-span-full md:order-none order-3">
              <PickPausedNotice pause={pickPause} />
            </div>
          {/if}
        </div>

        <GuidedPromptSuggestions {suggestions} onPromptSelected={handlePromptSelected} />
      {/if}
    </div>
  </div>
{/if}
