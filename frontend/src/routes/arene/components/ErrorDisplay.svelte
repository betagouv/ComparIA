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
  <div class="cg-border pe-13 lg:max-w-1/2 gap-4 bg-white p-4 pb-7 m-auto flex">
    <Icon icon="warning-fill" class="text-error" />
    <div>
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

      <div class="gap-5 md:grid-cols-2 grid">
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
            icon="checkbox-fill"
            iconPos="right"
            text={m['words.retry']()}
            onclick={() => onRetry()}
            class="w-full!"
          />
        {/if}
      </div>
    </div>
  </div>
</div>
