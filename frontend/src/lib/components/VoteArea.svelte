<script lang="ts">
  import type { VoteData } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import LikePanel from './LikePanel.svelte'
  import TextPrompt from './TextPrompt.svelte'
  import VoteRadioGroup from './VoteRadioGroup.svelte'

  let {
    value: form = $bindable(),
    disabled = false
  }: {
    value: VoteData
    disabled?: boolean
  } = $props()

  let showComments = $state(false)
</script>

<div id="vote-area" class="fr-container">
  <div class="text-center">
    <h4 class="mb-2!">{m['vote.title']()}</h4>
    <p class="text-grey fr-text--sm">{m['vote.introA']()}<br />{m['vote.introB']()}</p>
  </div>

  <VoteRadioGroup bind:value={form.selected} {disabled} />

  {#if form.selected}
    <div class="mt-11 flex flex-col gap-6 md:flex-row">
      {#each ['a', 'b'] as const as model (model)}
        <div
          class="c-border flex w-full flex-col gap-4 rounded-sm bg-white p-2 md:rounded-lg md:px-6 md:py-8"
        >
          <div class="flex items-center">
            <div class="c-bot-disk-{model}"></div>
            <p class="mb-0! ms-1! font-bold">{m[`models.names.${model}`]()}</p>
          </div>

          <p class="mb-0! font-bold">{m['vote.qualify.question']()}</p>

          <LikePanel
            show={true}
            kind="like"
            mode="vote"
            model={model.toUpperCase()}
            selection={form[model].like}
            {disabled}
          />
          <LikePanel
            show={true}
            kind="dislike"
            mode="vote"
            model={model.toUpperCase()}
            selection={form[model].dislike}
            {disabled}
          />

          {#if showComments}
            <TextPrompt
              id="comment-{model}"
              bind:value={form[model].comment}
              label={m['vote.qualify.question']()}
              placeholder={m['vote.qualify.placeholder']({ model: model.toUpperCase() })}
              rows={3}
              {disabled}
            />
          {/if}
        </div>
      {/each}
    </div>

    {#if !showComments}
      <div class="mt-4 text-center">
        <button class="link" {disabled} onclick={() => (showComments = true)}>
          {m['vote.qualify.addDetails']()}
        </button>
      </div>
    {/if}
  {/if}
</div>
