<script lang="ts">
  import type { APIModeAndPromptData, Mode, ModeInfos } from '$lib/chatService.svelte'
  import { modeInfos as choices } from '$lib/chatService.svelte'
  import Dropdown from '$lib/components/Dropdown.svelte'
  import GuidedPromptSuggestions from '$lib/components/GuidedPromptSuggestions.svelte'
  import Icon from '$lib/components/Icon.svelte'
  import ModelsSelection from '$lib/components/ModelsSelection.svelte'
  import TextPrompt from '$lib/components/TextPrompt.svelte'
  import { useLocalStorage } from '$lib/helpers/useLocalStorage.svelte'
  import { m } from '$lib/i18n/messages.js'
  import type { APIBotModel } from '$lib/models'
  import { tick } from 'svelte'
  import { fade } from 'svelte/transition'

  export let never_clicked: boolean = true
  export let models: APIBotModel[] = []
  export let elem_id = ''
  export let elem_classes: string[] = []
  export let visible = true
  export let disabled = false
  export let show_custom_models_selection: boolean = false
  export let onSubmit: (args: APIModeAndPromptData) => void

  let textboxElement: HTMLTextAreaElement

  const prompt = useLocalStorage('prompt', '', (parsed) => {
    if (parsed !== '') {
      tick().then(() => {
        if (textboxElement && typeof textboxElement.select === 'function') {
          textboxElement.select()
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
    if (textboxElement) {
      textboxElement.focus()
      if (start !== undefined && end !== undefined) {
        textboxElement.setSelectionRange(start, end)
        console.log(`[Textbox] Text selected from ${start} to ${end}`)
      } else {
        textboxElement.select()
        console.log('[Textbox] All text selected')
      }
    } else {
      console.error("[Textbox] Element 'el' not found for selection.")
    }
  }

  const findModelDetails = (id: string | null, modelsList: APIBotModel[]) => {
    if (!id || !modelsList || !Array.isArray(modelsList)) {
      return { name: m['words.random'](), iconPath: null }
    }
    const model = modelsList.find((m) => m.id === id)
    return {
      name: model?.simple_name ?? m['words.random'](),
      iconPath: model?.icon_path ?? null
    }
  }

  let choice: ModeInfos = get_choice(mode.value) || choices[0]
  let firstModelName = m['words.random']()
  let secondModelName = m['words.random']()
  let firstModelIconPath: string | null = null
  let secondModelIconPath: string | null = null

  $: {
    if (models && Array.isArray(models)) {
      if (mode.value === 'custom') {
        let firstDetails = findModelDetails(modelsSelection.value[0], models)
        let secondDetails = findModelDetails(modelsSelection.value[1], models)

        firstModelName = firstDetails.name
        firstModelIconPath = firstDetails.iconPath

        secondModelName = secondDetails.name
        secondModelIconPath = secondDetails.iconPath
      }
    } else {
      if (mode.value === 'custom') {
        console.error('Error: models is not a valid array, cannot apply custom selection.')
      }
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

  function onOptionSelected(index: number): void {
    if (index !== null && choices && choices.length > index) {
      choice = choices[index]
      mode.value = choice.value
    }
    show_custom_models_selection = mode.value === 'custom'
  }

  function toggle_model_selection(id: string): void {
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

  function get_choice(modeValue: Mode): ModeInfos | undefined {
    return choices.find((c) => c.value === modeValue)
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
      textboxElement &&
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
        '[Index] handlePromptSelected: No specific selection range provided, or textboxElement not ready. No text will be selected.',
        event.detail
      )
    }
    // Optionnellement, si on veut soumettre directement après sélection d'un prompt suggéré:
    // dispatchSubmit();
  }

  var alt_label: string = m['arenaHome.modelSelection']()
  $: if (
    (mode.value == 'custom' && modelsSelection.value.length < 1) ||
    (mode.value == 'random' && never_clicked)
  ) {
    alt_label = m['arenaHome.modelSelection']()
  } else {
    alt_label = choice.alt_label
  }
</script>

<div class:hidden={!visible} id={elem_id} class={elem_classes.join(' ') + ' fr-container'}>
  <h3 class="text-grey-200 fr-mt-md-12w fr-mb-md-7w fr-my-5w text-center">
    {m['arenaHome.title']()}
  </h3>
  <div class="grid">
    <div class="first-textbox fr-mb-3v">
      <TextPrompt
        id="initial-prompt"
        bind:el={textboxElement}
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
        on:click={() => {
          never_clicked = false
          show_custom_models_selection = false
        }}
      >
        <Icon icon="equalizer-fill" size="sm" block class="text-primary" />
        <span class="label">{alt_label}</span>
        <Icon icon="arrow-down-s-line" size="sm" />
      </button>
      {#if mode.value == 'custom' && modelsSelection.value.length > 0}
        <button
          {disabled}
          class="model-selection fr-mb-md-0 fr-mb-1w"
          data-fr-opened="false"
          aria-controls="modal-mode-selection"
        >
          <img
            src="/orgs/{firstModelIconPath}"
            alt={firstModelName}
            width="20"
            class="fr-mr-1v inline"
          />&thinsp;
          {firstModelName}
          <strong class="versus">&nbsp;vs.&nbsp;</strong>
          {#if secondModelIconPath != null}
            <img
              src="/orgs/{secondModelIconPath}"
              alt={secondModelName}
              width="20"
              class="fr-mr-1v inline"
            />&thinsp;
          {/if}
          {secondModelName}</button
        >
      {/if}
    </div>
    <input
      type="submit"
      class="submit-btn purple-btn btn"
      disabled={prompt.value == '' || disabled}
      on:click={() => dispatchSubmit()}
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
        class:fr-col-md-10={show_custom_models_selection}
        class:fr-col-md-5={!show_custom_models_selection}
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
            {#if show_custom_models_selection == false}
              <h6 id="modal-mode-selection" class="modal-title">
                {m['arenaHome.selectModels.question']()}
              </h6>
              <p>{m['arenaHome.selectModels.help']()}</p>
              <div>
                <Dropdown bind:mode={mode.value} {onOptionSelected} {choices} />
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
                    bind:custom_models_selection={modelsSelection.value}
                    {toggle_model_selection}
                  />
                  <div class="fr-mt-2w">
                    <button
                      class="btn fr-mb-md-0 fr-mb-1w"
                      on:click={() => (show_custom_models_selection = false)}
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
