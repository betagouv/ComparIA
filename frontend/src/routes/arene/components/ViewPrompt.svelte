<script lang="ts">
  import type { APIModeAndPromptData } from '$lib/chatService.svelte'
  import GuidedPromptSuggestions from '$lib/components/GuidedPromptSuggestions.svelte'
  import TextPrompt from '$lib/components/TextPrompt.svelte'
  import { useLocalStorage } from '$lib/helpers/useLocalStorage.svelte'
  import { m } from '$lib/i18n/messages.js'
  import { getModelsContext } from '$lib/models'
  import { tick } from 'svelte'
  import { ModelSelector } from '.'

  let { onSubmit }: { onSubmit: (args: APIModeAndPromptData) => void } = $props()

  let promptEl = $state<HTMLTextAreaElement>()
  let disabled = $state(false)

  const models = getModelsContext()

  const prompt = useLocalStorage('prompt', '', (parsed) => {
    if (parsed !== '') {
      tick().then(() => {
        if (promptEl && typeof promptEl.select === 'function') {
          promptEl.select()
        }
      })
    }
    return parsed
  })
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

  function dispatchSubmit(): void {
    disabled = true
    onSubmit({
      mode: mode.value,
      custom_models_selection: modelsSelection.value,
      prompt_value: prompt.value
    })
  }

  function handlePromptSelected(
    text: string,
    selectionStart?: number,
    selectionEnd?: number
  ): void {
    prompt.value = text
    console.log(
      `[Index] handlePromptSelected: Received promptselected. Text: "${prompt.value}", Start: ${selectionStart}, End: ${selectionEnd}`
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

<div id="prompt-area" class="fr-container">
  <h3 class="text-grey-200 fr-mt-md-12w fr-mb-md-7w fr-my-5w text-center">
    {m['arenaHome.title']()}
  </h3>
  <div class="grid">
    <div class="first-textbox fr-mb-3v">
      <TextPrompt
        id="initial-prompt"
        bind:el={promptEl}
        bind:value={prompt.value}
        label={m['arenaHome.prompt.label']()}
        placeholder={m['arenaHome.prompt.placeholder']()}
        {disabled}
        hideLabel
        rows={4}
        onSubmit={dispatchSubmit}
      />
    </div>

    <ModelSelector
      bind:mode={mode.value}
      bind:modelsSelection={modelsSelection.value}
      {models}
      {disabled}
    />

    <input
      type="submit"
      class="submit-btn purple-btn btn"
      disabled={prompt.value == '' || disabled}
      onclick={() => dispatchSubmit()}
      value={m['words.send']()}
    />
  </div>
  <div class="my-10 md:my-20">
    <GuidedPromptSuggestions onPromptSelected={handlePromptSelected} />
  </div>
</div>

<style>
  .versus {
    font-size: 1.125rem;
    margin: 0 5px;
    line-height: 0 !important;
  }

  .text-purple {
    color: #6a6af4;
  }

  .mode-selection-btn {
    --hover-tint: transparent;
    --active-tint: transparent;
    --focus-tint: transparent;
    display: flex;
    width: 100%;
    border-radius: 0.5em;
    border: 1px solid #e5e5e5 !important;
    flex-direction: row;
    padding: 0 0.5em 0 0.5em;
    align-items: center;
    text-align: left;
    font-weight: 500;
    font-size: 0.875em;
    color: #3a3a3a !important;
    background-color: white !important;
  }

  .model-selection {
    align-items: center;
    width: 100%;
    --hover-tint: transparent;
    --active-tint: transparent;
    --focus-tint: transparent;
    display: flex;
    border-radius: 0.5em;
    border: 1px solid #e5e5e5 !important;
    flex-direction: row;
    padding: 0.5em;

    text-align: left;
    font-weight: 500;
    font-size: 0.875em !important;
    color: #3a3a3a !important;
    background-color: white !important;
    max-height: 40px;
  }

  .mode-selection-btn .label {
    margin-left: 0.5em;
    flex-grow: 1;
    font-size: 0.875em;
  }

  .float-right {
    float: right;
  }

  .fr-modal__content {
    margin-bottom: 1em !important;
  }

  .fr-btn--close {
    color: #6a6af4 !important;
  }

  .fr-btn--close::after {
    background-color: #6a6af4 !important;
  }

  h6 {
    font-size: 1.125em;
  }

  .column {
    flex-direction: column;
  }
  .grid {
    display: grid;
    /* grid-template-columns: 1fr 1fr auto; */
  }
  .first-textbox {
    order: 1;
  }
  .mode-selection-btn {
    order: 0;
  }
  .submit-btn {
    order: 2;
    width: 100% !important;
  }
  /* .fr-modal__content { */
  .fr-modal__body {
    overflow-y: scroll;
  }

  @media (min-width: 48em) {
    .first-textbox,
    .mode-selection-btn {
      order: initial;
    }
    .submit-btn {
      width: 8.25rem !important;
    }
    .grid {
      grid-template-areas: 'text text' 'left right';
    }
    .first-textbox {
      grid-area: text;
    }

    .selections {
      grid-area: left;
      display: flex;
    }
    .mode-selection-btn {
      width: 260px;
    }
    .model-selection {
      width: fit-content;
    }

    .submit-btn {
      grid-area: right;
      justify-self: right;
    }
  }

  input[disabled] {
    cursor: not-allowed;
    /* background-color: var(--background-disabled-grey);
		color: var(--text-disabled-grey); */
    pointer-events: none;
  }
</style>
