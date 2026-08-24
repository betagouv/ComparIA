<script lang="ts">
  import { Button } from '$components/dsfr'
  import TextPrompt from '$components/TextPrompt.svelte'
  import type { APIModeAndPromptData } from '$lib/chatService.svelte'
  import type { ToolPublic } from '$lib/generated/backend'
  import { useLocalStorage } from '$lib/helpers/useLocalStorage.svelte'
  import { m } from '$lib/i18n/messages.js'
  import { getModelsContext } from '$lib/models'
  import type { SuggestionCategory } from '$lib/suggestions'
  import { sanitize } from '$lib/utils/commons'
  import { goto } from '$app/navigation'
  import { page } from '$app/state'
  import { onMount, tick } from 'svelte'
  import { SvelteURLSearchParams } from 'svelte/reactivity'
  import { GuidedPromptSuggestions, ModelSelector, ToolPicker } from '.'

  let {
    onPrompt,
    promptError,
    loading,
    suggestions,
    tools
  }: {
    onPrompt: (args: APIModeAndPromptData) => void
    promptError?: string
    loading: boolean
    suggestions: SuggestionCategory[]
    tools: ToolPublic[]
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
  let selectedTools = $state<string[]>([])

  const disabled = $derived(prompt == '' || !!promptError || loading)

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

  function onPromptSubmit() {
    onPrompt({
      mode: mode.value,
      custom_models_selection: modelsSelection.value,
      prompt_value: prompt,
      tools: selectedTools
    })
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
        <ToolPicker {tools} bind:selected={selectedTools} disabled={loading} />
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
