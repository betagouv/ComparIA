<script lang="ts">
  import ButtonPanel from '$lib/components/ButtonPanel.svelte'
  import Copy from '$lib/components/Copy.svelte'
  import Markdown from '$lib/components/markdown/MarkdownCode.svelte'
  import Pending from '$lib/components/Pending.svelte'
  import Brain from '$lib/icons/brain.svelte'
  import type { NormalisedMessage } from '$lib/types'
  import { sanitize } from '@gradio/sanitize'

  export let value: NormalisedMessage[]

  export let role = 'user'
  export let message: NormalisedMessage
  export let layout: 'bubble' | 'panel'
  // export let bubble_full_width: boolean;
  export let render_markdown: boolean
  export let latex_delimiters: {
    left: string
    right: string
    display: boolean
  }[]
  export let sanitize_html: boolean
  export let selectable: boolean
  export let rtl: boolean
  export let line_breaks: boolean
  export let root: string
  export let disabled = false
  var thought = ''
  var content = ''

  export let i: number
  export let show_copy_button: boolean
  export let generating: boolean
  export let thinking: boolean
  export let expand_reasoning: boolean = false
  export let show_reasoning: boolean
  export let show_like: boolean
  export let show_retry: boolean
  export let show_undo: boolean

  export let handle_action: (selected: string | null, value?: string[]) => void
  export let scroll: () => void

  function get_message_label_data(message: NormalisedMessage): string {
    return message.content
  }

  function get_message_bot_position(message: NormalisedMessage): string {
    if (message.role === 'assistant') {
      return message.metadata.bot === 'a' ? 'left' : 'right'
    } else {
      return ''
    }
  }

  type ButtonPanelProps = {
    disabled: boolean
    show: boolean
    handle_action: (selected: string | null) => void
    likeable: boolean
    show_retry: boolean
    show_undo: boolean
    generating: boolean
    show_copy_button: boolean
    message: NormalisedMessage[] | NormalisedMessage
    position: 'left' | 'right'
    layout: 'bubble' | 'panel'
  }

  let button_panel_props: ButtonPanelProps
  $: button_panel_props = {
    show: show_like || show_retry || show_undo || show_copy_button,
    handle_action,
    likeable: show_like,
    show_retry,
    show_undo,
    disabled,
    generating,
    show_copy_button,
    message: message,
    position: role === 'user' ? 'right' : 'left',
    layout
  }
  $: {
    thought = message.reasoning || ''
  }
  $: {
    content = message.content
  }
  $: {
    thinking = message.content == '' && generating
  }
  $: {
    show_reasoning = thinking || expand_reasoning
  }

  function toggleReasoning() {
    expand_reasoning = !expand_reasoning
  }
</script>

<!-- TODO: messages only has one message always... should simplify -->
<div
  class="message {role} {get_message_bot_position(message)}"
  class:message-markdown-disabled={!render_markdown}
>
  <button
    data-testid={role}
    class:latest={i === value.length - 1}
    class:message-markdown-disabled={!render_markdown}
    style:user-select="text"
    class:selectable
    style:cursor={selectable ? 'default' : 'default'}
    style:text-align={rtl ? 'right' : 'left'}
    dir={rtl ? 'rtl' : 'ltr'}
    aria-label={role + "'s message: " + get_message_label_data(message)}
  >
    <div class="message-content">
      {#if message.role === 'assistant'}
        <div class="model-title">
          {#if message.metadata?.bot === 'a'}
            <svg
              class="inline"
              width="26"
              height="32"
              name="disque violet (modèle A)"
              role="img"
              aria-label="disque violet (modèle A)"
              ><circle cx="13" cy="13" r="12" fill="#A96AFE" stroke="none"></circle></svg
            >
            <h3 class="inline">Modèle A</h3>
          {:else if message.metadata?.bot === 'b'}
            <svg
              class="inline"
              width="26"
              height="32"
              name="disque orange (modèle B)"
              role="img"
              aria-label="disque orange (modèle B)"
              ><circle cx="13" cy="13" r="12" fill="#ff9575" stroke="none"></circle></svg
            >
            <h3 class="inline">Modèle B</h3>
          {/if}
        </div>
        {#if thought != ''}
          <hr />
          <div class="fr-highlight fr-py-1w">
            <div class="text-purple fr-text--bold" on:click={toggleReasoning}>
              <svelte:component this={Brain} />&nbsp;{#if thinking}Raisonnement en cours...{:else}Raisonnement
                terminé{/if}
              <svg
                class="float-right inline"
                class:rotate={show_reasoning}
                width="20"
                height="20"
                viewBox="0 0 20 20"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  fill-rule="evenodd"
                  clip-rule="evenodd"
                  d="M9.99865 10.9766L14.1236 6.85156L15.302 8.0299L9.99865 13.3332L4.69531 8.0299L5.87365 6.85156L9.99865 10.9766Z"
                  fill="#6A6AF4"
                />
              </svg>
            </div>
            {#if show_reasoning}
              <div class="thought fr-mt-2w fr-mb-1w" on:click={toggleReasoning}>
                {@html sanitize(thought.split('\n').join('<br>'), root)}
              </div>
            {/if}
          </div>
          <hr />
        {/if}
        <Markdown
          message={content}
          {latex_delimiters}
          {sanitize_html}
          {render_markdown}
          {line_breaks}
          on:load={scroll}
        />
        {#if generating}
          <Pending />
        {/if}
      {:else}
        <Markdown
          message={message.content}
          {latex_delimiters}
          {sanitize_html}
          {render_markdown}
          {line_breaks}
          on:load={scroll}
        />
      {/if}
    </div>
    {#if message.role === 'assistant'}
      <ButtonPanel {...button_panel_props} />
    {:else}
      <div class="message-buttons-right">
        <Copy value={message.content} />
      </div>
    {/if}
  </button>
</div>

<style>
  .fr-highlight {
    padding-left: 1.25rem !important;
    margin-left: 0rem !important;
  }

  .float-right {
    float: right;
  }

  hr {
    padding: 1px !important;
  }

  .message-buttons-right {
    display: flex;
    float: right;
    gap: 0.5em;
  }

  .model-title {
    margin-bottom: 0.5em;
  }

  .message {
    position: relative;
    max-width: 100%;
  }

  .prose {
    color: var(--text-default-grey);
  }

  .message-content {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    overflow: auto;
    max-width: 100%;
  }

  .message.bot button {
    border-color: #e5e5e5;
    border-width: 1px;
    border-style: solid;
    /* border-radius: 0.5rem; */
    border-radius: 0.5rem;
    background-color: white;
    display: grid;
    height: 100%;
  }
  /* @media (min-width: 48em) {
		.message.bot button {
			height: 100%;
		}
	} */

  /* .message-row :global(img) {
		margin: var(--size-2);
		max-height: 300px;
	} */

  .message-markdown-disabled {
    white-space: pre-line;
  }

  @media (min-width: 48em) {
    .user {
      width: 60% !important;
    }
  }
  .user {
    width: 100%;
    margin-left: auto;
    background-color: var(--grey-950-100);
    --hover-tint: var(--grey-950-100);
    border-radius: 0.75rem;

    /* border-width: 1px;
		border-radius: var(--radius-md);
		align-self: flex-start;
		border-bottom-right-radius: 0;
		box-shadow: var(--shadow-drop);
		align-self: flex-start;
		text-align: right;
		padding: var(--spacing-sm) var(--spacing-xl);
		border-color: var(--border-color-accent-subdued);
		background-color: var(--color-accent-soft); */
  }

  .bot button,
  .bot button:hover,
  .bot button:active {
    background-color: white;
    --hover-tint: white;
    --active-tint: white;

    color: var(--text-default-grey);
  }

  .user button,
  .user button:hover,
  .user button:active {
    background-color: transparent;
    --hover-tint: transparent;
    --active-tint: transparent;

    color: var(--text-default-grey);
  }

  /* message content */
  /* {
		display: flex;
		flex-direction: column;
		width: calc(100% - var(--spacing-xxl));
		max-width: 100%;
		color: var(--body-text-color);
		font-size: var(--chatbot-text-size);
		overflow-wrap: break-word;
		width: 100%;
		height: 100%;
		border: none !important;
		box-shadow: none !important;
		display: flex;
		flex-direction: column;
		max-width: 100%;
		color: var(--body-text-color);
		font-size: var(--chatbot-text-size);
		overflow-wrap: break-word;
	} */

  /* .user {
		border-width: 1px;
		border-radius: var(--radius-md);
		align-self: flex-start;
		border-bottom-right-radius: 0;
		box-shadow: var(--shadow-drop);
		text-align: right;
		padding: var(--spacing-sm) var(--spacing-xl);
		border-color: var(--border-color-accent-subdued);
		background-color: var(--color-accent-soft);
	} */
  .rotate {
    transform: rotate(180deg);
    transition: transform 0.5s;
  }

  .thought {
    color: #666;
    font-style: italic;
  }

  .selectable {
    cursor: default;
  }

  .message > button {
    width: 100%;
    padding: 1.25rem;
    padding-right: 1.75rem;
  }
  .html {
    padding: 0;
    border: none;
    background: none;
  }

  .bot {
    margin-bottom: 1em;
  }
  /* On mobile, reorganize the panels */

  .bot.right {
    order: 1;
  }

  .text-purple {
    color: #6a6af4 !important;
  }

  @media (min-width: 48em) {
    .bot.right {
      order: inherit !important;
    }
  }

  h1,
  h2,
  h3,
  h4,
  h5,
  h6 {
    font-weight: 700;
    font-size: 1.25rem !important;
  }

  /* @media (min-width: 48em) {

	} */

  p {
    text-align: left !important;
    color: var(--text-active-grey);
  }

  ol,
  ul {
    font-size: initial !important;
    color: var(--text-active-grey);
  }
</style>
