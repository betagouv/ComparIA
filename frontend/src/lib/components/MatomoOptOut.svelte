<script lang="ts">
  import { getLocale } from '$lib/i18n/runtime'

  const { url }: { url: string } = $props()

  // Matomo names Norwegian Bokmål "nb", not "nb-NO".
  const language = $derived(getLocale().split('-')[0])
  // Matomo's opt-out script fills the div itself rather than loading an
  // iframe, so the CSP needs nothing more than its host in script-src.
  const src = $derived(
    `${url}/index.php?module=CoreAdminHome&action=optOutJS&divId=matomo-opt-out&language=${language}&showIntro=1`
  )
</script>

<div>
  <div id="matomo-opt-out"></div>
  <script {src}></script>
</div>
