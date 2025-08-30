<script lang="ts">
  import { Button } from '$components/dsfr'
  import TextPrompt from '$components/TextPrompt.svelte'
  import type { APIModeAndPromptData } from '$lib/chatService.svelte'
  import { useLocalStorage } from '$lib/helpers/useLocalStorage.svelte'
  import { m } from '$lib/i18n/messages.js'
  import { getModelsContext } from '$lib/models'
  import { tick } from 'svelte'
  import { GuidedPromptSuggestions, ModelSelector } from '.'

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

<div id="prompt-area" class="fr-container py-10 md:py-24">
  <h3 class="mb-0! text-center">
    {m['arenaHome.title']()}
  </h3>
  <div class="grid gap-3 py-10 md:grid-flow-row-dense md:grid-cols-3 md:pb-20 md:pt-12">
    <div class="order-1 md:order-none md:col-span-3">
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

    <Button
      type="submit"
      text={m['words.send']()}
      disabled={prompt.value == '' || disabled}
      class="w-full! md:w-auto! order-2 min-w-[130px] place-self-end md:order-none"
      onclick={() => dispatchSubmit()}
    />
  </div>
  <div class="pb-10">
    <GuidedPromptSuggestions onPromptSelected={handlePromptSelected} />
  </div>
</div>
