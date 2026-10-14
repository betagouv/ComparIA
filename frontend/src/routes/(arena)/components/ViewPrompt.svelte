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
    type PauseRefusal,
    type PickRefusal
  } from '$lib/chatService.svelte'
  import { useLocalStorage } from '$lib/helpers/useLocalStorage.svelte'
  import { m } from '$lib/i18n/messages.js'
  import { getModelsContext } from '$lib/models'
  import type { SuggestionCategory } from '$lib/suggestions'
  import { sanitize } from '$lib/utils/commons'
  import { onMount, tick } from 'svelte'
  import { SvelteURLSearchParams } from 'svelte/reactivity'
  import GuidedPromptSuggestions from './GuidedPromptSuggestions.svelte'
  import MessageUser from './MessageUser.svelte'
  import ModelSelector from './ModelSelector.svelte'
  import PauseNotice from './PauseNotice.svelte'
  import PickRefusalNotice from './PickRefusalNotice.svelte'

  let {
    onPrompt,
    promptError,
    pause,
    pickRefusal,
    loading,
    suggestions
  }: {
    onPrompt: (args: APIModeAndPromptData) => void | Promise<void>
    promptError?: string
    /** Set while an allowance is spent: the notice takes the place of the form. */
    pause?: PauseRefusal
    /** Set when the comparison asked for models the person may not use yet. */
    pickRefusal?: PickRefusal
    loading: boolean
    suggestions: SuggestionCategory[]
  } = $props()

  let promptEl = $state<HTMLTextAreaElement>()

  const models = getModelsContext().models.filter((model) => model.status === 'enabled')

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

  const disabled = $derived(prompt == '' || !!promptError || loading || submitting)
  const shownRefusal = $derived(pickRefusal === dismissedRefusal ? undefined : pickRefusal)
  const refusedNames = $derived(
    (shownRefusal?.limit.llm_ids ?? [])
      .map((id) => models.find((llm) => llm.id === id)?.name)
      .filter((name): name is string => !!name)
  )
  const modeInfos = getModeInfos()
  const selectedMode = $derived(modeInfos.find((item) => item.value === mode.value)!)

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
      if (refused?.length) {
        modelsSelection.value = modelsSelection.value.filter((id) => !refused.includes(id))
        if (!modelsSelection.value.length) {
          mode.value = 'random'
          toRandom = true
        }
      }
    } finally {
      submitting = false
    }
  }

  // Changed by the person, not by onPromptSubmit: the refusal no longer fits.
  function setMode(value: APIModeAndPromptData['mode']) {
    mode.value = value
    dismissedRefusal = pickRefusal
  }

  function setModelsSelection(value: string[]) {
    modelsSelection.value = value
    dismissedRefusal = pickRefusal
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

<!-- Present before loading starts so assistive technology announces the state change. -->
<p role="status" class="sr-only">{loading ? m['chatbot.loading']() : ''}</p>

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
      <h2 class="fr-h4 mb-0! text-center">
        {m['arenaHome.title']()}
      </h2>
      {#if pause}
        <div class="py-10">
          <PauseNotice refusal={pause} />
        </div>
      {:else}
        <div class="gap-3 py-10 md:grid-flow-row-dense md:grid-cols-6 grid">
          <div class="md:order-none md:col-span-full order-1">
            <TextPrompt
              id="initial-prompt"
              bind:el={promptEl}
              bind:value={prompt}
              label={m['arenaHome.prompt.label']()}
              placeholder={m['arenaHome.prompt.placeholder']()}
              bind:error={promptError}
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

          {#if shownRefusal}
            <div class="md:col-span-full">
              <PickRefusalNotice refusal={shownRefusal} names={refusedNames} {toRandom} />
            </div>
          {/if}

          <Button
            type="submit"
            text={m['words.send']()}
            {disabled}
            class="md:w-auto! md:order-none order-2 h-full w-full! min-w-[130px] place-self-end"
            onclick={() => onPromptSubmit()}
          />
        </div>

        <GuidedPromptSuggestions {suggestions} onPromptSelected={handlePromptSelected} />
      {/if}
    </div>
  </div>
{/if}
