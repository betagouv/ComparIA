<script lang="ts">
  import Dropdown from '$lib/components/Dropdown.svelte'
  import GuidedPromptSuggestions from '$lib/components/GuidedPromptSuggestions.svelte'
  import ModelsSelection from '$lib/components/ModelsSelection.svelte'
  import TextBox from '$lib/components/Textbox.svelte'
  import Brain from '$lib/icons/brain-customdropdown.svelte'
  import ChevronBas from '$lib/icons/chevron-bas.svelte'
  import Dice from '$lib/icons/dice.svelte'
  import Glass from '$lib/icons/glass.svelte'
  import Leaf from '$lib/icons/leaf.svelte'
  import Ruler from '$lib/icons/ruler.svelte'
  import type { Choice, Mode, ModeAndPromptData, Model } from '$lib/utils-customdropdown.ts'
  import type { LoadingStatus } from '@gradio/statustracker'
  import type { Gradio, KeyUpData } from '@gradio/utils'
  import { tick } from 'svelte'
  import { fade } from 'svelte/transition'

  export let never_clicked: boolean = true
  export let models: Model[] = []
  export let elem_id = ''
  export let elem_classes: string[] = []
  export let visible = true
  export let disabled = false

  export let gradio: Gradio<{
    change: ModeAndPromptData
    input: never
    submit: ModeAndPromptData
    select: ModeAndPromptData
    blur: never
    focus: never
    key_up: KeyUpData
    clear_status: LoadingStatus
  }>
  export let value_is_output = false
  export let lines: number = 4
  export let show_custom_models_selection: boolean = false
  export let max_lines: number = 4
  export let rtl = false
  export let text_align: 'left' | 'right' | undefined = undefined
  export let autofocus = false
  export let autoscroll = true
  export let interactive: boolean
  export let value: ModeAndPromptData

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
  let textboxElement: HTMLTextAreaElement | HTMLInputElement

  // let textboxElement: TextBox;
  export const choices: Choice[] = [
    {
      value: 'random',
      label: 'Aléatoire',
      alt_label: 'Modèles aléatoires',
      icon: Dice,
      description: 'Deux modèles tirés au hasard dans la liste'
    },
    {
      value: 'custom',
      label: 'Sélection manuelle',
      alt_label: 'Sélection manuelle',
      icon: Glass,
      description: ''
    },
    {
      value: 'small-models',
      label: 'Frugal',
      alt_label: 'Modèles frugaux',
      icon: Leaf,
      description: 'Deux modèles tirés au hasard parmi ceux de plus petite taille'
    },
    {
      value: 'big-vs-small',
      label: 'David contre Goliath',
      alt_label: 'David contre Goliath',
      icon: Ruler,
      description: 'Un petit modèle contre un grand, les deux tirés au hasard'
    },
    {
      value: 'reasoning',
      label: 'Raisonnement',
      alt_label: 'Modèles avec raisonnement',
      icon: Brain,
      description: 'Deux modèles tirés au hasard parmi ceux optimisés pour des tâches complexes'
    }
  ]

  const browser = typeof window !== 'undefined'

  function getCookie(name: string): string | null {
    if (!browser) return null
    const value = `; ${document.cookie}`
    const parts = value.split(`; ${name}=`)
    if (parts.length === 2) return parts.pop()!.split(';').shift() || null
    return null
  }

  function base64Encode(str: string): string {
    if (!browser) return str
    return btoa(encodeURIComponent(str))
  }

  function base64Decode(str: string): string {
    if (!browser) return str
    return decodeURIComponent(atob(str))
  }

  function setCookie(name: string, value: string, days = 7): void {
    if (!browser) return
    const date = new Date()
    date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000)
    document.cookie = `${name}=${value};expires=${date.toUTCString()};path=/`
  }

  function deleteCookie(name: string): void {
    if (!browser) return
    document.cookie = name + '=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;'
  }

  let initialMode: Mode = (getCookie('customdropdown_mode') as Mode) || 'random'

  function getInitialModels(availableModels: Model[]): string[] {
    if (!Array.isArray(availableModels)) {
      console.error('getInitialModels called without a valid availableModels array.')
      return []
    }

    if (typeof window !== 'undefined' && getCookie('customdropdown_models')) {
      try {
        const parsed = JSON.parse(getCookie('customdropdown_models')!)

        if (Array.isArray(parsed) && parsed.every((item) => typeof item === 'string')) {
          const availableModelIds = new Set(availableModels.map((m) => m.id))

          const validModels = parsed.filter((id) => availableModelIds.has(id))
          return validModels
        } else {
          return []
        }
      } catch (error) {
        console.error('Failed to parse models from cookie:', error)
        return []
      }
    }
    return []
  }

  const findModelDetails = (id: string | null, modelsList: Model[]) => {
    if (!id || !modelsList || !Array.isArray(modelsList)) {
      return { name: 'Aléatoire', iconPath: null }
    }
    const model = modelsList.find((m) => m.id === id)
    return {
      name: model?.simple_name ?? 'Aléatoire',
      iconPath: model?.icon_path ?? null
    }
  }

  let initialModels: string[] = getInitialModels(models) // Pass the populated models array

  let initialPrompt = ''
  if (browser) {
    const cookieValue = getCookie('comparia_initialprompt')
    if (cookieValue) {
      try {
        initialPrompt = base64Decode(cookieValue)
        deleteCookie('comparia_initialprompt')
        if (initialPrompt && typeof window !== 'undefined') {
          // Ensure browser context for tick
          tick().then(() => {
            if (textboxElement && typeof textboxElement.select === 'function') {
              textboxElement.select()
            }
          })
        }
      } catch (error) {
        console.error('Failed to decode prompt from cookie:', error)
        // initialPrompt remains ""
      }
    }
  }

  // Export the necessary variables
  export let mode: Mode = initialMode // Assuming initialMode is defined
  export let custom_models_selection: string[] = initialModels

  export let prompt_value: string = initialPrompt

  let choice: Choice = get_choice(initialMode) || choices[0]
  let firstModelName = 'Aléatoire'
  let secondModelName = 'Aléatoire'
  let firstModelIconPath: string | null = null
  let secondModelIconPath: string | null = null

  $: {
    if (models && Array.isArray(models)) {
      if (mode === 'custom') {
        let firstDetails = findModelDetails(custom_models_selection?.[0], models)
        let secondDetails = findModelDetails(custom_models_selection?.[1], models)

        firstModelName = firstDetails.name
        firstModelIconPath = firstDetails.iconPath

        secondModelName = secondDetails.name
        secondModelIconPath = secondDetails.iconPath
      }
    } else {
      if (mode === 'custom') {
        console.error('Error: models is not a valid array, cannot apply custom selection.')
      }
    }
  }

  function dispatchSelect(): void {
    // console.log("selecting")
    // console.log(mode)
    // console.log(custom_models_selection)
    // console.log("not sending value")
    // console.log(value)

    // Save to cookies
    setCookie('customdropdown_mode', mode)
    setCookie('customdropdown_models', JSON.stringify(custom_models_selection))
    gradio.dispatch('select', {
      mode: mode,
      custom_models_selection: custom_models_selection,
      prompt_value: prompt_value
    })
  }

  function dispatchSubmit(): void {
    // console.log("submitting")
    // console.log(mode)
    // console.log(custom_models_selection)
    // console.log("not sending value")
    // console.log(value)

    // Save to cookies
    setCookie('customdropdown_mode', mode)
    setCookie('customdropdown_models', JSON.stringify(custom_models_selection))
    setCookie('comparia_initialprompt', base64Encode(prompt_value))
    gradio.dispatch('submit', {
      mode: mode,
      custom_models_selection: custom_models_selection,
      prompt_value: prompt_value
    })
  }

  function handle_option_selected(index: number): void {
    if (index !== null && choices && choices.length > index) {
      mode = choices[index].value
      if (mode !== value['mode']) {
        value['mode'] = mode
        // Don't tell backend to switch to custom if no custom_models_selection yet
        if (!(mode === 'custom' && custom_models_selection.length === 0)) {
          dispatchSelect()
        }
        choice = choices[index]
      }
    }
    show_custom_models_selection = mode === 'custom'
  }

  function toggle_model_selection(id: string): void {
    if (!custom_models_selection.includes(id)) {
      if (custom_models_selection.length < 2) {
        custom_models_selection.push(id)
      }
    } else {
      custom_models_selection = custom_models_selection.filter((item) => item !== id)
    }
    value['custom_models_selection'] = custom_models_selection
    dispatchSelect()

    // If clicked on second model, close model selection modal
    if (custom_models_selection.length === 2) {
      const modeSelectionModal = document.getElementById('modal-mode-selection')
      if (modeSelectionModal) {
        window.setTimeout(() => {
          // @ts-ignore - DSFR is globally available
          window.dsfr(modeSelectionModal).modal.conceal()
        }, 300)
      }
    }
  }

  // Dispatch change from cookie
  if (browser && (initialMode !== 'random' || initialModels.length > 0)) {
    value['mode'] = mode
    value['custom_models_selection'] = custom_models_selection
    dispatchSelect()
  }

  function get_choice(modeValue: Mode): Choice | undefined {
    return choices.find((c) => c.value === modeValue)
  }

  // Handle prompt value update from backend
  $: {
    if (value_is_output) {
      prompt_value = value['prompt_value']
    } else {
      if (value['prompt_value'] != prompt_value) {
        value['prompt_value'] = prompt_value
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
    prompt_value = event.detail.text
    console.log(
      `[Index] handlePromptSelected: Received promptselected. Text: "${prompt_value}", Start: ${event.detail.selectionStart}, End: ${event.detail.selectionEnd}`
    )
    // Déclencher un événement de changement pour que Gradio soit informé
    gradio.dispatch('change', {
      prompt_value: prompt_value,
      mode: mode,
      custom_models_selection: custom_models_selection
    })

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
    // disabled = true;
  }

  var alt_label: string = 'Sélection des modèles'
  $: if (
    // eslint-disable-next-line
    (mode == 'custom' && custom_models_selection.length < 1) ||
    (mode == 'random' && never_clicked)
  ) {
    alt_label = 'Sélection des modèles'
  } else {
    alt_label = choice.alt_label
  }
</script>

<div class:hidden={!visible} id={elem_id} class={elem_classes.join(' ') + ' fr-container'}>
  <h3 class="text-grey-200 fr-mt-md-12w fr-mb-md-7w fr-my-5w text-center">
    Comment puis-je vous aider aujourd'hui ?
  </h3>
  <div class="grid">
    <div class="first-textbox fr-mb-3v">
      <TextBox
        bind:el={textboxElement}
        {disabled}
        bind:value={prompt_value}
        bind:value_is_output
        {elem_id}
        {elem_classes}
        {visible}
        {lines}
        {rtl}
        {text_align}
        max_lines={!max_lines ? lines + 1 : max_lines}
        placeholder="Écrivez votre premier message ici"
        {autofocus}
        {autoscroll}
        on:change={() => {
          gradio.dispatch('change', {
            prompt_value: prompt_value,
            mode: mode,
            custom_models_selection: custom_models_selection
          })
        }}
        on:submit={() => {
          dispatchSubmit()
          disabled = true
        }}
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
        <svg
          width="18"
          height="18"
          viewBox="0 0 18 18"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M4.14161 14.0003C4.4848 13.0293 5.41083 12.3337 6.49935 12.3337C7.58785 12.3337 8.51393 13.0293 8.8571 14.0003H17.3327V15.667H8.8571C8.51393 16.638 7.58785 17.3337 6.49935 17.3337C5.41083 17.3337 4.4848 16.638 4.14161 15.667H0.666016V14.0003H4.14161ZM9.1416 8.16699C9.48477 7.196 10.4108 6.50033 11.4993 6.50033C12.5878 6.50033 13.5139 7.196 13.8571 8.16699H17.3327V9.83366H13.8571C13.5139 10.8047 12.5878 11.5003 11.4993 11.5003C10.4108 11.5003 9.48477 10.8047 9.1416 9.83366H0.666016V8.16699H9.1416ZM4.14161 2.33366C4.4848 1.36267 5.41083 0.666992 6.49935 0.666992C7.58785 0.666992 8.51393 1.36267 8.8571 2.33366H17.3327V4.00033H8.8571C8.51393 4.97132 7.58785 5.66699 6.49935 5.66699C5.41083 5.66699 4.4848 4.97132 4.14161 4.00033H0.666016V2.33366H4.14161Z"
            fill="#6A6AF4"
          />
        </svg>
        <span class="label"> {alt_label}</span><span class="chevron"
          ><svelte:component this={ChevronBas} />
        </span></button
      >
      {#if mode == 'custom' && custom_models_selection.length > 0}
        <button
          {disabled}
          class="model-selection fr-mb-md-0 fr-mb-1w"
          data-fr-opened="false"
          aria-controls="modal-mode-selection"
        >
          <img
            src="../assets/orgs/{firstModelIconPath}"
            alt={firstModelName}
            width="20"
            class="fr-mr-1v inline"
          />&thinsp;
          {firstModelName}
          <strong class="versus">&nbsp;vs.&nbsp;</strong>
          {#if secondModelIconPath != null}
            <img
              src="../assets/orgs/{secondModelIconPath}"
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
      disabled={prompt_value == '' || disabled}
      on:click={() => {
        dispatchSubmit()
        disabled = true
      }}
      value="Envoyer"
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
              aria-controls="modal-mode-selection">Fermer</button
            >
          </div>
          <div class="fr-modal__content fr-pb-4w">
            {#if show_custom_models_selection == false}
              <h6 id="modal-mode-selection" class="modal-title">
                Quels modèles voulez-vous comparer ?
              </h6>
              <p>Sélectionnez le mode de comparaison qui vous convient</p>
              <div>
                <Dropdown
                  {handle_option_selected}
                  {choices}
                  bind:mode
                  on:select={(e) => gradio.dispatch('select', e.detail)}
                  disabled={!interactive}
                />
              </div>
            {:else}
              <div in:fade>
                <h6 id="modal-mode-selection" class="modal-title">
                  Quels modèles voulez-vous comparer ?
                  <span class="text-purple fr-ml-2w">
                    {custom_models_selection.length}/2 modèles
                  </span>
                </h6>
                <p class="fr-mb-2w">
                  Si vous n’en choisissez qu’un, le second sera sélectionné de manière aléatoire
                </p>
                <div>
                  <ModelsSelection {models} bind:custom_models_selection {toggle_model_selection} />
                  <div class="fr-mt-2w">
                    <button
                      class="btn fr-mb-md-0 fr-mb-1w"
                      on:click={() => (show_custom_models_selection = false)}>Retour</button
                    >
                    <button
                      aria-controls="modal-mode-selection"
                      class="btn purple-btn float-right"
                      on:click={() =>
                        gradio.dispatch('select', {
                          prompt_value: prompt_value,
                          mode: mode,
                          custom_models_selection: custom_models_selection
                        })}>Valider</button
                    >
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

  .chevron {
    line-height: 0;
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

  .mode-selection-btn svg {
    flex-grow: 0;
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
