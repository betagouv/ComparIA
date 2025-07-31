<script lang="ts">
  import Tooltip from '$lib/components/Tooltip.svelte'
  import { global } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { sanitize } from '$lib/utils/commons'

  const NumberFormater = $derived(
    new Intl.NumberFormat(global.locale, { maximumSignificantDigits: 3 })
  )
  const votes = $derived(
    global.votes
      ? {
          count: NumberFormater.format(global.votes.count),
          objective: NumberFormater.format(global.votes.objective),
          ratio: (100 * (global.votes.count / global.votes.objective)).toFixed() + '%'
        }
      : null
  )
</script>

<div class="counter">
  <span class="fr-ml-1w legende">
    {m['header.chatbot.vote.total']()}&nbsp;<Tooltip
      id="gauge"
      size="xs"
      label={m['header.chatbot.vote.legend']()}
    >
      {@html sanitize(m['header.chatbot.vote.tooltip']())}
    </Tooltip>
  </span>
  <div class="linear-gauge" style:--gauge-ratio={votes?.ratio}>
    <div class="linear-gauge-fill">
      <span class="votes">{votes?.count}</span>
    </div>
  </div>
  <span class="objectif">{m['header.chatbot.vote.objective']()}{votes?.objective}</span>
</div>

<style>
  .legende {
    font-size: 0.875em;
    color: #161616 !important;
    font-weight: bold;
  }

  .votes {
    font-size: 0.75em;
    font-weight: bold;
    color: #695240 !important;
    margin-left: 5px;
    height: inherit;
    float: left;
  }

  .objectif {
    font-weight: 500;
    font-size: 0.75em;
    color: #7f7f7f !important;
  }

  .linear-gauge-fill {
    width: 0%; /* Start at 0% for the animation */
    height: 100%;
    border-radius: 4px;
    background-color: #fde39c !important;
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
    width: 200px;
    height: 20px;
    background: #fff;
    border-radius: 4px;
    border: 1px solid #cccccc;
    overflow: hidden;
  }

  .counter {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1em;
    /* padding-top: 0;
    padding-bottom: 1em; */
    height: auto;
  }

  .objectif {
    display: block;
  }
</style>
