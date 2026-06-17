<script lang="ts">
  import { Button, Toggle, Tooltip } from '$components/dsfr'
  import TextPrompt from '$components/TextPrompt.svelte'
  import type { APIModeAndPromptData } from '$lib/chatService.svelte'
  import { useLocalStorage } from '$lib/helpers/useLocalStorage.svelte'
  import { m } from '$lib/i18n/messages.js'
  import { getModelsContext } from '$lib/models'
  import { sanitize } from '$lib/utils/commons'
  import { tick } from 'svelte'
  import { GuidedPromptSuggestions, ModelSelector } from '.'

  let {
    onPrompt,
    promptError,
    loading
  }: {
    onPrompt: (args: APIModeAndPromptData) => void
    promptError?: string
    loading: boolean
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

  const disabled = $derived(prompt == '' || !!promptError || loading)

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
      web_search: webSearch
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
    <h3 class="mb-0! text-center">
      {m['arenaHome.title']()}
    </h3>
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
      <GuidedPromptSuggestions onPromptSelected={handlePromptSelected} />
    </div>
  </div>
</div>
