<script>
  import Textbox from '$lib/Textbox.svelte';
  import { currentScreen, textValue, isLoading, mode, customModelsDropdown } from '$lib/stores';
  import Chatbots from '$lib/Chatbots.svelte';
  import { sendChatMessage } from '$lib/chatService';

  const availableModes = ['random', 'specific'];
  const availableModels = ['model1', 'model2', 'model3'];

  async function handleSubmit() {
    currentScreen.set('Chatbots');
    await sendChatMessage();
  }

  function updateMode(newMode) {
    mode.set(newMode);
  }

  function toggleModel(model) {
    const currentModels = get(customModelsDropdown);
    if (currentModels.includes(model)) {
      customModelsDropdown.set(currentModels.filter((m) => m !== model));
    } else {
      customModelsDropdown.set([...currentModels, model]);
    }
  }
</script>

<div class="settings-container">
  <div class="mode-selector">
    <label>Mode:</label>
    <select bind:value={$mode} on:change={(e) => updateMode(e.target.value)}>
      {#each availableModes as m}
        <option value={m} selected={$mode === m}>{m}</option>
      {/each}
    </select>
  </div>

  <div class="models-selector">
    <label>Custom Models:</label>
    {#each availableModels as model}
      <label>
        <input
          type="checkbox"
          checked={$customModelsDropdown.includes(model)}
          on:change={() => toggleModel(model)}
        />
        {model}
      </label>
    {/each}
  </div>
</div>

<Textbox bind:value={$textValue} />
<button on:click={handleSubmit} disabled={$isLoading}>
  {#if $isLoading}
    Sending...
  {:else}
    Send
  {/if}
</button>

<style>
  .settings-container {
    margin-bottom: 1rem;
    display: flex;
    gap: 2rem;
  }

  .mode-selector,
  .models-selector {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  select {
    padding: 0.5rem;
    border: 1px solid #ccc;
    border-radius: 4px;
  }

  input[type='checkbox'] {
    margin-right: 0.5rem;
  }
</style>
