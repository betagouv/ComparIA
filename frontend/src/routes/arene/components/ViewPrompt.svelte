<script lang="ts">
  import { Icon } from '$components/dsfr'
  import type { APIModeAndPromptData } from '$lib/chatService.svelte'
  import { modeInfos as modeChoices } from '$lib/chatService.svelte'
  import Dropdown from '$lib/components/Dropdown.svelte'
  import GuidedPromptSuggestions from '$lib/components/GuidedPromptSuggestions.svelte'
  import ModelsSelection from '$lib/components/ModelsSelection.svelte'
  import TextPrompt from '$lib/components/TextPrompt.svelte'
  import { useLocalStorage } from '$lib/helpers/useLocalStorage.svelte'
  import { m } from '$lib/i18n/messages.js'
  import { getModelsContext } from '$lib/models'
  import { tick } from 'svelte'
  import { fade } from 'svelte/transition'

  let { onSubmit }: { onSubmit: (args: APIModeAndPromptData) => void } = $props()

  let promptEl = $state<HTMLTextAreaElement>()
  let neverClicked = $state(true)
  let disabled = $state(false)
  let showModelsSelection = $state(false)

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

  const choice = $derived(modeChoices.find((c) => c.value === mode.value) || modeChoices[0])
  const { modelA, modelB } = $derived({
    modelA: models.find((model) => model.id === modelsSelection.value[0]),
    modelB: models.find((model) => model.id === modelsSelection.value[1])
  })
  const altLabel = $derived.by(() => {
    if (
      (mode.value == 'custom' && modelsSelection.value.length < 1) ||
      (mode.value == 'random' && neverClicked)
    ) {
      return m['arenaHome.modelSelection']()
    } else {
      return choice.alt_label
    }
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

  function toggleModelSelection(id: string): void {
    if (!modelsSelection.value.includes(id)) {
      if (modelsSelection.value.length < 2) {
        modelsSelection.value.push(id)
      }
    } else {
      modelsSelection.value = modelsSelection.value.filter((item) => item !== id)
    }

    // If clicked on second model, close model selection modal
    if (modelsSelection.value.length === 2) {
      const modeSelectionModal = document.getElementById('modal-mode-selection')
      if (modeSelectionModal) {
        window.setTimeout(() => {
          // @ts-ignore - DSFR is globally available
          window.dsfr(modeSelectionModal).modal.conceal()
        }, 300)
      }
    }
  }

  function handlePromptSelected(
    event: CustomEvent<{
      text: string
      selectionStart?: number
      selectionEnd?: number
    }>
  ): void {
    prompt.value = event.detail.text
    console.log(
      `[Index] handlePromptSelected: Received promptselected. Text: "${prompt.value}", Start: ${event.detail.selectionStart}, End: ${event.detail.selectionEnd}`
    )
    if (
      promptEl &&
      event.detail.selectionStart !== undefined &&
      event.detail.selectionEnd !== undefined
    ) {
      const sStart = event.detail.selectionStart
      const sEnd = event.detail.selectionEnd

      const performSelection = () => {
        if (selectPartialText && typeof selectPartialText === 'function') {
          console.log(`[Index] Performing selection. Start: ${sStart}, End: ${sEnd}`)
          selectPartialText(sStart, sEnd)
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
        event.detail
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

    <div class="selections">
      <button
        class="mode-selection-btn fr-py-1w fr-py-md-0 fr-mb-md-0 fr-mb-1w fr-mr-3v"
        data-fr-opened="false"
        {disabled}
        aria-controls="modal-mode-selection"
        onclick={() => {
          neverClicked = false
          showModelsSelection = false
        }}
      >
        <Icon icon="equalizer-fill" size="sm" block class="text-primary" />
        <span class="label">{altLabel}</span>
        <Icon icon="arrow-down-s-line" size="sm" />
      </button>
      {#if mode.value == 'custom' && modelA}
        <button
          {disabled}
          class="model-selection fr-mb-md-0 fr-mb-1w"
          data-fr-opened="false"
          aria-controls="modal-mode-selection"
        >
          <img
            src="/orgs/ai/{modelA.icon_path}"
            alt={modelA.simple_name}
            width="20"
            class="fr-mr-1v inline"
          />&thinsp;{modelA.simple_name}
          <strong class="versus">&nbsp;vs.&nbsp;</strong>
          {#if modelB}
            <img
              src="/orgs/ai/{modelB.icon_path}"
              alt={modelB.simple_name}
              width="20"
              class="fr-mr-1v inline"
            />&thinsp;{modelB.simple_name}
          {:else}
            {m['words.random']()}
          {/if}
        </button>
      {/if}
    </div>
    <input
      type="submit"
      class="submit-btn purple-btn btn"
      disabled={prompt.value == '' || disabled}
      onclick={() => dispatchSubmit()}
      value={m['words.send']()}
    />
  </div>
  <div class="fr-mb-3v">
    <GuidedPromptSuggestions on:promptselected={handlePromptSelected} />
  </div>
</div>
<dialog aria-labelledby="modal-mode-selection" id="modal-mode-selection" class="fr-modal">
  <div class="fr-container fr-container--fluid fr-container-md">
    <div class="fr-grid-row fr-grid-row--center">
      <div
        class="fr-col-12"
        class:fr-col-md-10={showModelsSelection}
        class:fr-col-md-5={!showModelsSelection}
      >
        <div class="fr-modal__body">
          <div class="fr-modal__header">
            <button
              class="fr-btn--close fr-btn"
              title="Fermer la fenêtre modale"
              aria-controls="modal-mode-selection"
            >
              {m['words.close']()}
            </button>
          </div>
          <div class="fr-modal__content fr-pb-4w">
            {#if showModelsSelection == false}
              <h6 id="modal-mode-selection" class="modal-title">
                {m['arenaHome.selectModels.question']()}
              </h6>
              <p>{m['arenaHome.selectModels.help']()}</p>
              <div>
                <Dropdown
                  bind:mode={mode.value}
                  choices={modeChoices}
                  onOptionSelected={(mode) => (showModelsSelection = mode === 'custom')}
                />
              </div>
            {:else}
              <div in:fade>
                <h6 id="modal-mode-selection" class="modal-title">
                  {m['arenaHome.compareModels.question']()}
                  <span class="text-purple fr-ml-2w">
                    {m['arenaHome.compareModels.count']({ count: modelsSelection.value.length })}
                  </span>
                </h6>
                <p class="fr-mb-2w">
                  {m['arenaHome.compareModels.help']()}
                </p>
                <div>
                  <ModelsSelection
                    {models}
                    bind:selection={modelsSelection.value}
                    {toggleModelSelection}
                  />
                  <div class="fr-mt-2w">
                    <button
                      class="btn fr-mb-md-0 fr-mb-1w"
                      onclick={() => (showModelsSelection = false)}
                    >
                      {m['words.back']()}
                    </button>
                    <button aria-controls="modal-mode-selection" class="btn purple-btn float-right">
                      {m['words.validate']()}
                    </button>
                  </div>
                </div>
              </div>
            {/if}
          </div>
        </div>
      </div>
    </div>
  </div>
</dialog>

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
