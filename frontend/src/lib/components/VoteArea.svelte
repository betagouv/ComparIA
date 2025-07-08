<script lang="ts">
  import BaseRadio from '$lib/components/Radio.svelte'
  import type { LoadingStatus } from '@gradio/statustracker'
  import { StatusTracker } from '@gradio/statustracker'
  import type { Gradio, SelectData } from '@gradio/utils'

  export let gradio: Gradio<{
    change: never
    select: SelectData
    input: never
    clear_status: LoadingStatus
  }>

  // export let label = gradio.i18n("radio.radio");
  // export let info: string | undefined = undefined;
  export let elem_id = ''
  export let elem_classes: string[] = []
  export let visible = true
  export let value: string | null = null
  export let choices: string[] = []
  // export let show_label = true;
  // export let container = false;
  // export let scale: number | null = null;
  export let min_columns: number | undefined = 2
  export let loading_status: LoadingStatus
  export let interactive = true

  let columns = Math.min(choices.length, 4) // max 4 columns

  function handle_change(): void {
    gradio.dispatch('change')
  }

  $: value, handle_change()

  $: disabled = !interactive
</script>

<div id={elem_id} class="flex justify-center {elem_classes} {visible ? '' : 'hide'}">
  <StatusTracker
    autoscroll={gradio.autoscroll}
    i18n={gradio.i18n}
    {...loading_status}
    on:clear_status={() => gradio.dispatch('clear_status', loading_status)}
  />

  {#each choices as [display_value, internal_value], i (i)}
    <BaseRadio
      {display_value}
      {internal_value}
      bind:selected={value}
      {disabled}
      on:input={() => {
        gradio.dispatch('select', { value: internal_value, index: i })
        gradio.dispatch('input')
      }}
    />
  {/each}
</div>

<!-- TODO: this in svelte based on what's in customchatbot  -->
<!-- with gr.Column(
	# h-screen
	visible=True,
	elem_classes="fr-container min-h-screen fr-pt-4w",
	elem_id="vote-area",
) as vote_area:
	
	with gr.Row(
		visible=False,
		elem_id="supervote-area",
		# FIXME: bottom margin too imprecise
		elem_classes="fr-grid-row fr-grid-row--gutters gap-0 fr-mt-8w fr-mb-md-16w fr-mb-16w",
	) as supervote_area:

		with gr.Column(
			elem_classes="fr-col-12 fr-col-md-6 fr-mr-md-n1w fr-mb-1w bg-white rounded-tile"
		):

			gr.HTML(
				value="""<p><svg class="inline" width='26' height='26'><circle cx='13' cy='13' r='12' fill='#A96AFE' stroke='none'/></svg> <strong>Modèle A</strong></p>
<p class="fr-mb-2w"><strong>Comment qualifiez-vous ses réponses ?</strong></p>"""
			)

			positive_a = gr.CheckboxGroup(
				elem_classes="thumb-up-icon flex-important checkboxes fr-mb-2w",
				show_label=False,
				choices=[
					("Utiles", "useful"),
					("Complètes", "complete"),
					("Créatives", "creative"),
					("Mise en forme claire", "clear-formatting"),
				],
			)

			negative_a = gr.CheckboxGroup(
				elem_classes="thumb-down-icon flex-important checkboxes fr-mb-2w",
				show_label=False,
				choices=[
					("Incorrectes", "incorrect"),
					("Superficielles", "superficial"),
					("Instructions non respectées", "instructions-not-followed"),
				],
			)

			comments_a = FrInput(
				show_label=False,
				visible=False,
				lines=3,
				placeholder="Les réponses du modèle A sont...",
			)

		with gr.Column(
			elem_classes="fr-col-12 fr-col-md-6 fr-ml-md-3w fr-mr-md-n3w fr-mb-1w bg-white rounded-tile"
		):

			gr.HTML(
				value="""<p><svg class="inline" width='26' height='26'><circle cx='13' cy='13' r='12' fill='#ff9575' stroke='none'/></svg> <strong>Modèle B</strong></p>
<p class="fr-mb-2w"><strong>Comment qualifiez-vous ses réponses ?</strong></p>"""
			)

			positive_b = gr.CheckboxGroup(
				elem_classes="thumb-up-icon flex-important checkboxes fr-mb-2w",
				show_label=False,
				choices=[
					("Utiles", "useful"),
					("Complètes", "complete"),
					("Créatives", "creative"),
					("Mise en forme claire", "clear-formatting"),
				],
			)

			negative_b = gr.CheckboxGroup(
				elem_classes="thumb-down-icon flex-important checkboxes fr-mb-2w",
				show_label=False,
				choices=[
					("Incorrectes", "incorrect"),
					("Superficielles", "superficial"),
					("Instructions non respectées", "instructions-not-followed"),
				],
			)
			comments_b = FrInput(
				show_label=False,
				visible=False,
				lines=3,
				placeholder="Les réponses du modèle B sont...",
			)
		comments_link = gr.Button(
			elem_classes="link fr-mt-1w", value="Ajouter des détails"
		) -->

<style>
  /* .wrap {
		display: flex;
		flex-wrap: wrap;
		gap: var(--checkbox-label-gap);
	} */
</style>
