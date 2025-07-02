<script lang="ts">
  import { sendChatMessage } from './chatService'
  import { conversation, hasError, isLoading } from './stores'

  async function submitRequest() {
    await sendChatMessage()
  }
</script>

<div class="arena-container">
  {#if $isLoading}
    <div class="loader"></div>
  {:else if $hasError}
    <div class="error-message">
      <p>Une erreur est survenue lors de l'envoi du message</p>
      <button on:click={submitRequest}>Réessayer</button>
    </div>
  {:else}
    <div class="chatbots-grid">
      <div class="chatbot">
        <h3>Chatbot 1</h3>
        <div class="chatbot-content">
          {#each $conversation.chatbot1 as message, index}
            <div
              class:user-message={message.role === 'user'}
              class:assistant-message={message.role === 'assistant'}
            >
              <span class="message-index">#{index}</span>
              {message.content}
              <div class="message-actions">
                <button class="like-btn">👍</button>
                <button class="dislike-btn">👎</button>
              </div>
            </div>
          {/each}
        </div>
      </div>

      <div class="chatbot">
        <h3>Chatbot 2</h3>
        <div class="chatbot-content">
          {#each $conversation.chatbot2 as message, index}
            <div
              class:user-message={message.role === 'user'}
              class:assistant-message={message.role === 'assistant'}
            >
              <span class="message-index">#{index}</span>
              {message.content}
              <div class="message-actions">
                <button class="like-btn">👍</button>
                <button class="dislike-btn">👎</button>
              </div>
            </div>
          {/each}
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .arena-container {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100%;
    flex-direction: column;
    gap: 1rem;
  }

  .chatbots-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2rem;
    width: 100%;
  }

  .chatbot {
    border: 1px solid #eee;
    padding: 1rem;
    border-radius: 8px;
  }

  .loader {
    border: 4px solid rgba(0, 0, 0, 0.1);
    border-radius: 50%;
    border-top: 4px solid #3498db;
    width: 40px;
    height: 40px;
    animation: spin 1s linear infinite;
  }

  .error-message {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
    color: #e74c3c;
  }

  .user-message {
    background-color: #e3f2fd;
    padding: 8px 12px;
    border-radius: 8px;
    margin: 4px 0;
    max-width: 80%;
    align-self: flex-end;
  }

  .assistant-message {
    background-color: #f5f5f5;
    padding: 8px 12px;
    border-radius: 8px;
    margin: 4px 0;
    max-width: 80%;
    align-self: flex-start;
  }

  .error-message button {
    padding: 0.5rem 1rem;
    background: #e74c3c;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }

  .message-index {
    color: #777;
    font-size: 0.8em;
    margin-right: 0.5em;
  }

  .message-actions {
    display: flex;
    gap: 0.5em;
    margin-top: 0.5em;
  }

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
  }
</style>
