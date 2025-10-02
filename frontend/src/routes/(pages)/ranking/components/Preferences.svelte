<script lang="ts">
  import { m } from '$lib/i18n/messages'
  import type { BotModel } from '$lib/models'
  import { PreferencesTable } from '.'

  let { data, onDownloadData }: { data: BotModel[]; onDownloadData: () => void } = $props()
</script>

<div id="ranking-preferences">
  <h2 class="fr-h6 text-primary! mb-4!">{m['ranking.preferences.title']()}</h2>
  <p class="text-[14px]! text-dark-grey mb-10!">{m['ranking.preferences.desc']()}</p>

  <PreferencesTable id="preferences-table" {data} {onDownloadData} />
</div>
