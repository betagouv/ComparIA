<script>
  import { m } from '$lib/i18n/messages'
</script>

<svg
  class="fr-responsive-img"
  width="513"
  height="287"
  viewBox="0 0 513 287"
  fill="none"
  version="1.1"
  id="comment-ca-marche"
  xmlns="http://www.w3.org/2000/svg"
  role="group"
  aria-labelledby="svg-title svg-desc"
>
  <title id="svg-title">{m['home.intro.steps.title']()}</title>
  <desc id="svg-desc">{m['home.intro.steps.a11yDesc']()}</desc>

  <path
    d="m 6,21.5 c 1.97844,129.342 213.429,38.6375 252,85 38.571,46.362 -185.2601,50.665 -152,117.5"
    class="stroke-black"
    id="line"
  />

  <circle cx="5.5" cy="18.5" r="5.5" class="fill-primary" />
  <path
    d="M21.56 28.96V6.52L15.76 9.8L13.08 5.96L21.72 0.959999H26.96V28.96H21.56Z"
    class="fill-primary"
  />
  <text x="39.528667" y="9.3315382" class="svg-title">{m['home.intro.steps.one.title']()}</text>
  <text x="39.899445" y="34.194839">
    <tspan>{m['home.intro.steps.one.a']()}</tspan>
    <tspan x="39.907349" y="60.237579">{m['home.intro.steps.one.b']()}</tspan>
  </text>

  <circle cx="258.5" cy="107.5" r="5.5" class="fill-primary" />
  <path
    d="M270.32 122V117.12L279.92 107.68C282.08 105.48 283.44 103.96 283.44 101.68C283.44 99.36 281.84 98 279.64 98C276.96 98 275.32 99.64 273.84 102.12L269.44 99.44C271.8 95.6 275.28 93.2 280.16 93.2C285.04 93.2 288.96 96.32 288.96 101.12C288.96 104.96 286.44 107.92 283.68 110.6L276.92 117.12H289.68V122H270.32Z"
    class="fill-primary"
  />
  <text x="146.80658" y="222.71048" class="svg-title">{m['home.intro.steps.three.title']()}</text>
  <text x="146.46295" y="248.50197">
    <tspan>{m['home.intro.steps.three.a']()}</tspan>
    <tspan x="146.52148" y="275.85373">{m['home.intro.steps.three.b']()}</tspan>
  </text>

  <circle cx="105.5" cy="225.5" r="5.5" class="fill-primary" />
  <path
    d="M138.04 235C138.04 240.32 133.68 243.8 127.84 243.8C122.56 243.8 119.16 241.48 116.88 237.48L121.6 234.56C123.16 237.64 125.04 239 127.8 239C130.52 239 132.56 237.36 132.56 234.76C132.56 232.2 130.56 230.6 127.6 230.6H123V225.8H127.24C129.6 225.8 131.32 224.48 131.32 222.32C131.32 220.2 129.72 219 127.52 219C125.28 219 123.76 220.2 122.6 222.2L118.2 219.48C120.24 216.16 123.4 214.2 127.92 214.2C133.04 214.2 136.84 217.12 136.84 221.72C136.84 224.32 135.72 226.52 133.64 227.96C136.48 229.4 138.04 231.92 138.04 235Z"
    class="fill-primary"
  />
  <text x="298.69144" y="102.10426" class="svg-title">{m['home.intro.steps.two.title']()}</text>
  <text x="299.24356" y="128">
    <tspan>{m['home.intro.steps.two.a']()}</tspan>
    <tspan x="299.25146" y="154.04274">{m['home.intro.steps.two.b']()}</tspan>
  </text>
</svg>

<style>
  text {
    font-family: Marianne;
    font-size: 14px;
    fill: var(--grey-425-625);
    dominant-baseline: central;
    line-height: 24px;
  }

  text.svg-title {
    font-family: Marianne;
    font-size: 18px;
    font-weight: 700;
    fill: var(--grey-50-1000);
    dominant-baseline: central;
    line-height: 28px;
  }
</style>
