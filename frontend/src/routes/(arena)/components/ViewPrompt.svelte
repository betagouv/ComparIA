<script lang="ts">
  import Pending from '$components/Pending.svelte'
  import { Button, Icon, Toggle, Tooltip } from '$components/dsfr'
  import TextPrompt from '$components/TextPrompt.svelte'
  import { modeInfos, type APIModeAndPromptData } from '$lib/chatService.svelte'
  import { useLocalStorage } from '$lib/helpers/useLocalStorage.svelte'
  import { m } from '$lib/i18n/messages.js'
  import { getModelsContext } from '$lib/models'
  import type { SuggestionCategory } from '$lib/suggestions'
  import { sanitize } from '$lib/utils/commons'
  import { goto } from '$app/navigation'
  import { page } from '$app/state'
  import { onMount, tick } from 'svelte'
  import { SvelteURLSearchParams } from 'svelte/reactivity'
  import GuidedPromptSuggestions from './GuidedPromptSuggestions.svelte'
  import MessageUser from './MessageUser.svelte'
  import ModelSelector from './ModelSelector.svelte'

  let {
    onPrompt,
    promptError,
    loading,
    suggestions
  }: {
    onPrompt: (args: APIModeAndPromptData) => void | Promise<void>
    promptError?: string
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

  const disabled = $derived(prompt == '' || !!promptError || loading || submitting)
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
    goto(qs ? `${page.url.pathname}?${qs}` : page.url.pathname, { replaceState: true })
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
    try {
      await onPrompt({
        mode: mode.value,
        custom_models_selection: modelsSelection.value,
        prompt_value: prompt,
        web_search: webSearch
      })
    } finally {
      submitting = false
    }
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
  <div id="prompt-area" class="fr-container py-10 md:py-24">
    <div class="fr-col-xl-8 m-auto">
      <h2 class="fr-h3 mb-0! text-center">
        {m['arenaHome.title']()}
      </h2>
      <div class="gap-3 py-10 md:grid-flow-row-dense md:grid-cols-6 md:pb-20 md:pt-12 grid">
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
            bind:mode={mode.value}
            bind:modelsSelection={modelsSelection.value}
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

        <Button
          type="submit"
          text={m['words.send']()}
          {disabled}
          class="md:w-auto! md:order-none order-2 h-full w-full! min-w-[130px] place-self-end"
          onclick={() => onPromptSubmit()}
        />
      </div>
      <div class="pb-10">
        <GuidedPromptSuggestions {suggestions} onPromptSelected={handlePromptSelected} />
      </div>
    </div>
  </div>
{/if}
