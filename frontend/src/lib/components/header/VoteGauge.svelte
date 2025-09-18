<script lang="ts">
  import { Tooltip } from '$components/dsfr'
  import { getVotesContext } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { sanitize } from '$lib/utils/commons'

  let { id }: { id: string } = $props()

  const NumberFormater = new Intl.NumberFormat(getLocale())
  const votesData = getVotesContext()
  const votes = $derived({
    count: NumberFormater.format(votesData.count),
    objective: NumberFormater.format(votesData.objective),
    ratio: (100 * (votesData.count / votesData.objective)).toFixed() + '%'
  })
</script>

{#if votes}
  <div class="flex w-full items-center justify-center gap-3 text-xs lg:gap-1">
    <div
      class="linear-gauge w-full max-w-[260px] grow rounded-sm lg:w-[160px]"
      style:--gauge-ratio={votes?.ratio}
    >
      <div class="linear-gauge-fill rounded-sm">
        <span class="vote-count ms-2 whitespace-nowrap align-middle font-bold">
          {m['header.votes.count']({ count: votes.count })}
        </span>
      </div>
    </div>
    <span class="objective font-medium">
      {m['header.votes.objective']({ count: votes.objective })}&nbsp;<Tooltip
        {id}
        size="xs"
        label={m['header.votes.legend']()}
      >
        {@html sanitize(m['header.votes.tooltip']())}
      </Tooltip>
    </span>
  </div>
{/if}

<style>
  .vote-count {
    color: #695240;
  }

  .linear-gauge-fill {
    width: 0%; /* Start at 0% for the animation */
    height: 100%;
    background-color: #fde39c;
    /* Add the transition property */
    transition: width 1s ease-out 0.5s; /* 1s duration, ease-out timing, 0.5s delay */
  }

  /* This keyframe animation sets the final width after the delay */
  @keyframes fillGauge {
    to {
      width: var(--gauge-ratio);
    }
  }

  /* Apply the animation to the linear-gauge-fill */
  .linear-gauge-fill {
    animation: fillGauge 1s ease-out 0.5s forwards; /* Same duration, timing, and delay */
  }

  .linear-gauge {
    height: 20px;
    background: #fff;
    border: 1px solid #cccccc;
    overflow: hidden;
  }

  .objective {
    color: #7f7f7f;
  }
</style>
