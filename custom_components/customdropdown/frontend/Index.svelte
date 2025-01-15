<script context="module" lang="ts">
	export { default as BaseDropdown } from "./shared/Dropdown.svelte";
	export { default as BaseExample } from "./Example.svelte";
</script>

<script lang="ts">
	import type { Gradio, KeyUpData, SelectData } from "@gradio/utils";
	import Dropdown from "./shared/Dropdown.svelte";
	import { Block } from "@gradio/atoms";
	import { StatusTracker } from "@gradio/statustracker";
	import type { LoadingStatus } from "@gradio/statustracker";

	type Item = string | number;

	export let info: string | undefined = undefined;
	export let elem_id = "";
	export let elem_classes: string[] = [];
	export let visible = true;
	export let multiselect = false;
	export let value: Item | Item[] | undefined = multiselect ? [] : undefined;

	import Glass from "./shared/glass.svelte";
	import Leaf from "./shared/leaf.svelte";
	import Ruler from "./shared/ruler.svelte";
	import Dice from "./shared/dice.svelte";

	// Hardcoded options
	export const choices = [
		{
			value: "random",
			label: "Aléatoire",
			icon: Dice, // Replace with your icon class or SVG
			description: "Deux modèles choisis au hasard parmi toute la liste",
		},
		{
			value: "small-models",
			label: "Économe",
			icon: Leaf, // Replace with your icon class or SVG
			description:
				"Minimisez votre impact environnemental avec deux petits modèles",
		},
		{
			value: "big-vs-small",
			label: "Petit contre grand",
			icon: Ruler, // Replace with your icon class or SVG
			description:
				"Comparez les performances d’un petit modèle contre un grand",
		},
		// {
		// 	value: "custom",
		// 	label: "Sélection manuelle",
		// 	icon: Glass, // Replace with your icon class or SVG
		// 	description:
		// 		"Sélectionnez vous-même jusqu’à deux modèles à comparer",
		// },
	];

	export let container = true;
	export let scale: number | null = null;
	export let min_width: number | undefined = undefined;
	// export let allow_custom_value = false;
	export let gradio: Gradio<{
		change: never;
		input: never;
		select: SelectData;
		blur: never;
		focus: never;
		key_up: KeyUpData;
		clear_status: LoadingStatus;
	}>;
	export let interactive: boolean;
	$: console.log(value);
	var choice;
	$: choice = choices.find((item) => item.value === value);
</script>

<Block
	{visible}
	{elem_id}
	{elem_classes}
	padding={container}
	allow_overflow={false}
	{scale}
	{min_width}
>
	<button data-fr-opened="false" aria-controls="modal-mode-selection">
		<!-- <button
		data-fr-opened="false"
		aria-controls="modal-mode-selection"
		on:click={() => {
			commented = true;
			handle_action("commenting");
		}}> -->
		<svelte:component this={choice.icon} />

		<strong>{choice.label}</strong>
		<p>{choice.description}</p></button
	>
</Block>

<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
<!-- <dialog
	aria-labelledby="modal-mode-selection"
	id="modal-mode-selection"
	class="fr-modal"
	on:blur={() => {
		sendComment(commenting);
	}}
	on:keydown={(e) => {
		if (e.key === "Escape") {
			sendComment(commenting);
		}
	}}
> -->
<dialog
	aria-labelledby="modal-mode-selection"
	id="modal-mode-selection"
	class="fr-modal"
>
	<div class="fr-container fr-container--fluid fr-container-md">
		<div class="fr-grid-row fr-grid-row--center">
			<div class="fr-col-12 fr-col-md-8 fr-col-lg-6">
				<div class="fr-modal__body">
					<div class="fr-modal__header">
						<button
							class="fr-btn--close fr-btn"
							title="Fermer la fenêtre modale"
							aria-controls="modal-mode-selection">Fermer</button
						>
						<!-- <button
							class="fr-btn--close fr-btn"
							title="Fermer la fenêtre modale"
							aria-controls="modal-mode-selection"
							on:click={() => sendComment(commenting)}
							>Fermer</button
						> -->
					</div>
					<div class="fr-modal__content">
						<h3 id="modal-mode-selection" class="modal-title">
							Quels modèles voulez-vous comparer ?
						</h3>
						<p>
							Sélectionnez le mode de comparaison qui vous
							convient
						</p>
						<div>
							<Dropdown
								{choices}
								bind:value
								on:change={() => gradio.dispatch("change")}
								on:input={() => gradio.dispatch("input")}
								on:select={(e) =>
									gradio.dispatch("select", e.detail)}
								on:blur={() => gradio.dispatch("blur")}
								on:focus={() => gradio.dispatch("focus")}
								on:key_up={(e) =>
									gradio.dispatch("key_up", e.detail)}
								disabled={!interactive}
							/>
							<button
								aria-controls="modal-mode-selection"
								class="btn purple-btn">Envoyer</button
							>

							<!-- <button
								aria-controls="modal-mode-selection"
								class="btn purple-btn"
								on:click={() => sendComment(commenting)}
								>Envoyer</button
							> -->
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</dialog>
