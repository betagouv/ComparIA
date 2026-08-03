<script lang="ts">
  import { Button, Icon, Link } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import type { ClassValue } from 'svelte/elements'

  let {
    error,
    class: classes,
    onRetry
  }: {
    error: string
    class?: ClassValue
    onRetry: () => void
  } = $props()
</script>

<div class={['fr-container', classes]}>
  <div class="cg-border gap-3 bg-white p-5 m-auto flex max-w-[38rem] items-start">
    <Icon icon="warning-fill" class="mt-1 text-error shrink-0" />
    <div class="min-w-0 flex-1">
      {#if error === 'Context too long.'}
        <h6 class="mb-2!">{m['chatbot.errors.tooLong.title']()}</h6>
        <p>
          {m['chatbot.errors.tooLong.message']()}&nbsp;{m[`chatbot.errors.tooLong.retry`]()}
        </p>
      {:else}
        <h6 class="mb-2!">{m['chatbot.errors.other.title']()}</h6>
        <p>
          {m['chatbot.errors.other.message']()}<br />
          {m['chatbot.errors.other.retry']()}.
          <span class="hidden">{error}</span>
        </p>
      {/if}

      <div class="mt-4 flex">
        {#if error === 'Context too long.'}
          <Link
            button
            icon="refresh-line"
            iconPos="right"
            variant="secondary"
            href="../arene/"
            text={m['words.restart']()}
            class="w-full!"
          />
        {:else}
          <Button
            icon="refresh-line"
            iconPos="right"
            text={m['words.retry']()}
            onclick={() => onRetry()}
            variant="secondary"
          />
        {/if}
      </div>
    </div>
  </div>
</div>
