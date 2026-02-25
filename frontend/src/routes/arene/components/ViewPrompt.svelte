<script lang="ts">
  import { Button } from '$components/dsfr'
  import TextPrompt from '$components/TextPrompt.svelte'
  import type { APIModeAndPromptData } from '$lib/chatService.svelte'
  import { runChatBots } from '$lib/chatService.svelte'
  import { useLocalStorage } from '$lib/helpers/useLocalStorage.svelte'
  import { m } from '$lib/i18n/messages.js'
  import { getModelsContext } from '$lib/models'
  import { tick } from 'svelte'
  import { GuidedPromptSuggestions, ModelSelector } from '.'

  let promptEl = $state<HTMLTextAreaElement>()
  let disabled = $state(false)
  let webSearch = $state(false)

  const models = getModelsContext().models.filter((model) => model.status === 'enabled')
  let prompt = $state('')
  let promptError = $state<string>()
  // const prompt = useLocalStorage('prompt', '', (parsed) => {
  //   if (parsed !== '') {
  //     tick().then(() => {
  //       if (promptEl && typeof promptEl.select === 'function') {
  //         promptEl.select()
  //       }
  //     })
  //   }
  //   return parsed
  // })
  const mode = useLocalStorage<APIModeAndPromptData['mode']>('mode', 'random')
  const modelsSelection = useLocalStorage<string[]>('customModelsSelection', [], (parsed) => {
    if (Array.isArray(parsed) && parsed.every((item) => typeof item === 'string')) {
      const availableModelIds = new Set(models.map((m) => m.id))
      return parsed.filter((id) => availableModelIds.has(id))
    }
    return []
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

  async function dispatchSubmit(): void {
    disabled = true
    const validationError = await runChatBots({
      mode: mode.value,
      custom_models_selection: modelsSelection.value,
      prompt_value: prompt,
      web_search: webSearch
    })
    if (validationError) {
      promptError = validationError
      disabled = false
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

      // Initial attempt: After Svelte tick and browser paint
      tick().then(() => {
        requestAnimationFrame(() => {
          performSelection()
        })
      })

      // // Second attempt: With a short delay
      // setTimeout(() => {
      // 	performSelection();
      // }, 100); // 100ms delay

      // // Third attempt: With a slightly longer delay
      // setTimeout(() => {
      // 	performSelection();
      // }, 250); // 250ms delay
    } else {
      // No valid selection range provided
      console.log(
        '[Index] handlePromptSelected: No specific selection range provided, or promptEl not ready. No text will be selected.',
        { text, selectionStart, selectionEnd }
      )
    }
    // Optionnellement, si on veut soumettre directement après sélection d'un prompt suggéré:
    // dispatchSubmit();
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
          {disabled}
          hideLabel
          rows={4}
          onSubmit={dispatchSubmit}
        />
      </div>

      <div class="md:order-none md:col-span-5 order-3 flex items-center gap-3">
        <button
          type="button"
          class="web-search-toggle shrink-0"
          class:active={webSearch}
          disabled={disabled}
          onclick={() => (webSearch = !webSearch)}
          title={m['arenaHome.webSearch.title']()}
          aria-pressed={webSearch}
        >
          <span class="i-ri-global-line text-lg" aria-hidden="true"></span>
          <span class="text-sm">{webSearch ? m['arenaHome.webSearch.enabled']() : m['arenaHome.webSearch.disabled']()}</span>
        </button>

        <ModelSelector
          bind:mode={mode.value}
          bind:modelsSelection={modelsSelection.value}
          {models}
          {disabled}
        />
      </div>

      <Button
        type="submit"
        text={m['words.send']()}
        disabled={prompt == '' || !!promptError || disabled}
        class="md:w-auto! md:order-none order-2 w-full! min-w-[130px] place-self-end"
        onclick={() => dispatchSubmit()}
      />
    </div>
    <div class="pb-10">
      <GuidedPromptSuggestions onPromptSelected={handlePromptSelected} />
    </div>
  </div>
</div>

<style lang="postcss">
  .web-search-toggle {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.375rem;
    height: 2.5rem;
    padding: 0 0.75rem;
    border-radius: 0.5rem;
    border: 1px solid var(--border-default-grey);
    background: var(--background-default-grey);
    color: var(--text-mention-grey);
    cursor: pointer;
    white-space: nowrap;
    transition:
      background-color 0.2s,
      color 0.2s,
      border-color 0.2s;

    &:hover:not(:disabled) {
      border-color: var(--blue-france-main-525);
      color: var(--blue-france-main-525);
    }

    &.active {
      background: var(--blue-france-main-525) !important;
      border-color: var(--blue-france-main-525) !important;
      color: white !important;
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }
</style>
