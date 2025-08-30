<script lang="ts">
  import { m } from '$lib/i18n/messages'
  import type { SvelteHTMLElements } from 'svelte/elements'

  let {
    message = m['words.loading'](),
    ...props
  }: { message?: string } & SvelteHTMLElements['div'] = $props()
</script>

<div
  {...props}
  class={['flex flex-col items-center py-5', props.class]}
  role="status"
  aria-label={m['words.loading']()}
  aria-live="polite"
>
  <div class="mb-1 h-[15px] w-[15px]">
    <div class="disc left"></div>
    <div class="disc right"></div>
  </div>
  <p class="mb-0!">
    <strong>{message}</strong>
  </p>
</div>

<style>
  .disc {
    position: absolute;
    width: 15px; /* Adjust disc size as needed */
    height: 15px; /* Adjust disc size as needed */
    border-radius: 50%;
  }

  .disc.left {
    background-color: var(--cg-orange);
    animation: animate-left 1.5s infinite ease-in-out;
  }

  .disc.right {
    background-color: var(--cg-purple);
    animation: animate-right 1.5s infinite ease-in-out;
  }

  @keyframes animate-left {
    0% {
      transform: translateX(-10px); /* Initial offset from center, full size */
      z-index: 2; /* Starts on top */
    }
    49.9% {
      z-index: 2; /* Keep high z-index before flip */
    }
    50% {
      /* Move from -15px to +15px (total 30px to the right) */
      transform: translateX(calc(10px));
      z-index: 0; /* Drops behind after passing */
    }
    99.9% {
      z-index: 0; /* Keep low z-index before returning */
    }
    100% {
      transform: translateX(-10px); /* Return to original position and size */
      z-index: 2; /* Back on top for next cycle */
    }
  }

  /* --- Animation for the Right Disc (Moves left, then back) --- */
  @keyframes animate-right {
    0% {
      transform: translateX(10px); /* Initial offset from center, full size */
      z-index: 1; /* Starts behind */
    }
    49.9% {
      z-index: 1; /* Keep low z-index before flip */
    }
    50% {
      transform: translateX(calc(-10px));
      z-index: 3; /* Jumps to the front after passing */
    }
    99.9% {
      z-index: 3; /* Keep high z-index before returning */
    }
    100% {
      transform: translateX(10px); /* Return to original position and size */
      z-index: 1; /* Back behind for next cycle */
    }
  }
</style>
