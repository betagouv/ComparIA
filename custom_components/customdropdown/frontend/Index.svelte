<script context="module" lang="ts">
	export { default as BaseDropdown } from "./shared/Dropdown.svelte";
</script>

<script lang="ts">
	import type { Gradio, KeyUpData, SelectData } from "@gradio/utils";
	import Dropdown from "./shared/Dropdown.svelte";
	import { Block } from "@gradio/atoms";
	import type { LoadingStatus } from "@gradio/statustracker";
	import TextBox from "./shared/Textbox.svelte";

	import { ModeAndPromptData } from "./shared/utils.ts";

	type Item = string | number;
	export let models: [] = [];
	export let elem_id = "";
	export let elem_classes: string[] = [];
	export let visible = true;
	export let mode: "random" | "custom" | "big-vs-small" | "small-models" =
		"random";
	export let prompt_value: string = ""; // Initialize as an empty string by default
	export let custom_models_selection: Item[] = []; // Default to an empty list

	// Prompt value
	// export let value: string = ""
	// Combine all into one value object based on mode and other properties
	export let value: {
		prompt_value: string;
		mode: "random" | "custom" | "big-vs-small" | "small-models";
		custom_models_selection: Item[];
	} = {
		prompt_value: "",
		mode: "random",
		custom_models_selection: [],
	};

	// // Combine all into one value object based on mode and other properties
	$: {
		// Reassign to ensure the latest values are always used
		value = {
			prompt_value: prompt_value,
			mode: mode,
			custom_models_selection: custom_models_selection,
		};
		console.log("value");
		console.log(value);
		console.log("prompt_value");
		console.log(prompt_value);
		console.log("mode");
		console.log(mode);
		// prompt_value = value.prompt_value;
	}

	// Add reactive statements to update props when value changes
	// $: prompt_value = value["prompt_value"];
	// $: mode = value.mode;
	// $: custom_models_selection = value["custom_models_selection"];

	// export let value: Item | Item[] | undefined = multiselect ? [] : undefined;

	import Glass from "./shared/glass.svelte";
	import Leaf from "./shared/leaf.svelte";
	import Ruler from "./shared/ruler.svelte";
	import Dice from "./shared/dice.svelte";
	import { SvelteComponent } from "svelte";

	export const choices = [
		{
			value: "random",
			label: "Aléatoire",
			alt_label: "Modèles aléatoires",
			icon: Dice, // Replace with your icon class or SVG
			description: "Deux modèles choisis au hasard parmi toute la liste",
		},
		{
			value: "small-models",
			label: "Économe",
			alt_label: "Modèles économes",

			icon: Leaf, // Replace with your icon class or SVG
			description:
				"Minimisez votre impact environnemental avec deux petits modèles",
		},
		{
			value: "big-vs-small",
			label: "Petit contre grand",
			alt_label: "Petit contre grand modèle",
			icon: Ruler, // Replace with your icon class or SVG
			description:
				"Comparez les performances d’un petit modèle contre un grand",
		},
		// {
		// 	value: "custom",
		// 	label: "Sélection manuelle",
		// 	alt_label: "Sélection manuelle",
		// 	icon: Glass, // Replace with your icon class or SVG
		// 	description:
		// 		"Sélectionnez vous-même jusqu’à deux modèles à comparer",
		// },
	];

	export let container = true;
	export let scale: number | null = null;
	export let min_width: number | undefined = undefined;
	// export let allow_custom_value = false;
	// FIXME: types for events
	export let gradio: Gradio<{
		change: typeof value;
		input: never;
		submit: ModeAndPromptData;
		// submit: never;
		select: ModeAndPromptData;
		// select: SelectData;
		blur: never;
		focus: never;
		key_up: KeyUpData;
		clear_status: LoadingStatus;
	}>;

	export let label = "Textbox";
	export let lines: number;
	export let show_custom_models_selection: boolean = false;
	export let placeholder = "";
	export let show_label: boolean;
	export let max_lines: number;
	export let type: "text" | "password" | "email" = "text";
	// export let scale: number | null = null;
	// export let min_width: number | undefined = undefined;
	export let show_copy_button = false;
	// export let value_is_output = false;
	export let rtl = false;
	export let text_align: "left" | "right" | undefined = undefined;
	export let autofocus = false;
	export let autoscroll = true;

	export let interactive: boolean;
	var choice;
	// FIXME: maybe do a apply(oldValue, newValue) here?
	$: {
		console.log("choices");
		console.log(choices);
		console.log("value");
		console.log(value);
		console.log("prompt_value");
		console.log(prompt_value);
		console.log("mode");
		console.log(mode);
		choice = choices.find((item) => item.value === mode);
	}
	// $: choice = choices.find((item) => item.value["mode"] === mode);
	// $: choice = choices.find((item) => item.mode === mode);
</script>

<h4 class="text-center text-grey-200 fr-mt-4w fr-mb-2w">
	Comment puis-je vous aider aujourd'hui ?
</h4>
<Block
	{visible}
	{elem_id}
	{elem_classes}
	padding={container}
	allow_overflow={false}
	{scale}
	{min_width}
>
	<!-- FIXME: Make input send prompt_value -->
	<!-- FIXME: Change gradio.dispatch"change" value type -->
	<!-- value=bind:prompt_value -->
	<TextBox
		bind:value={prompt_value}
		{elem_id}
		{elem_classes}
		{visible}
		{label}
		{show_label}
		{lines}
		{type}
		{rtl}
		{text_align}
		max_lines={!max_lines ? lines + 1 : max_lines}
		{placeholder}
		{show_copy_button}
		{autofocus}
		{autoscroll}
		on:submit={() =>
			gradio.dispatch("submit", {
				prompt_value: prompt_value,
				mode: mode,
				custom_models_selection: custom_models_selection,
			})}
	/>

	<!-- on:change={() =>
	gradio.dispatch("change", {
		prompt_value: prompt_value,
		mode: mode,
		custom_models_selection: custom_models_selection,
	})}
on:input={() => gradio.dispatch("input")}
		on:blur={() => gradio.dispatch("blur")}
		on:focus={() => gradio.dispatch("focus")}
		disabled={!interactive} -->

	<button
		class="mode-selection-btn"
		data-fr-opened="false"
		aria-controls="modal-mode-selection"
	>
		<svg
			width="18"
			height="18"
			viewBox="0 0 18 18"
			fill="none"
			xmlns="http://www.w3.org/2000/svg"
		>
			<path
				d="M4.14161 14.0003C4.4848 13.0293 5.41083 12.3337 6.49935 12.3337C7.58785 12.3337 8.51393 13.0293 8.8571 14.0003H17.3327V15.667H8.8571C8.51393 16.638 7.58785 17.3337 6.49935 17.3337C5.41083 17.3337 4.4848 16.638 4.14161 15.667H0.666016V14.0003H4.14161ZM9.1416 8.16699C9.48477 7.196 10.4108 6.50033 11.4993 6.50033C12.5878 6.50033 13.5139 7.196 13.8571 8.16699H17.3327V9.83366H13.8571C13.5139 10.8047 12.5878 11.5003 11.4993 11.5003C10.4108 11.5003 9.48477 10.8047 9.1416 9.83366H0.666016V8.16699H9.1416ZM4.14161 2.33366C4.4848 1.36267 5.41083 0.666992 6.49935 0.666992C7.58785 0.666992 8.51393 1.36267 8.8571 2.33366H17.3327V4.00033H8.8571C8.51393 4.97132 7.58785 5.66699 6.49935 5.66699C5.41083 5.66699 4.4848 4.97132 4.14161 4.00033H0.666016V2.33366H4.14161Z"
				fill="#6A6AF4"
			/>
		</svg>
		<span> {choice.alt_label}</span></button
	>
	<input
		type="submit"
		class="purple-btn btn"
		on:submit={() =>
			gradio.dispatch("submit", {
				prompt_value: prompt_value,
				mode: mode,
				custom_models_selection: custom_models_selection,
			})}
	/>
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
					</div>
					<div class="fr-modal__content">
						{#if show_custom_models_selection == false}
							<h6 id="modal-mode-selection" class="modal-title">
								Quels modèles voulez-vous comparer ?
							</h6>
							<p>
								Sélectionnez le mode de comparaison qui vous
								convient
							</p>
							<div>
								<Dropdown
									{choices}
									bind:mode
									on:select={(e) => {
										console.log("on:select e");
										console.log(e);
				// 						gradio.dispatch("select", {
				// "prompt_value": prompt_value,
				// "mode": mode,
				// "custom_models_selection": custom_models_selection,});
										gradio.dispatch("select", e.detail);
									}}
									disabled={!interactive}
								/>
								<!-- <Dropdown
									{choices}
									bind:mode
									on:input={() => gradio.dispatch("input")}
									on:select={(e) =>
										gradio.dispatch("select", e.detail)}
									on:blur={() => gradio.dispatch("blur")}
									on:focus={() => gradio.dispatch("focus")}
									on:key_up={(e) =>
										gradio.dispatch("key_up", e.detail)}
									disabled={!interactive}
								/> -->
								<div class="fr-mt-2w">
									<button
										aria-controls="modal-mode-selection"
										class="btn">Annuler</button
									>
									<button
										aria-controls="modal-mode-selection"
										class="btn purple-btn float-right"
										>Envoyer</button
									>
								</div>
								<!-- <button
								aria-controls="modal-mode-selection"
								class="btn purple-btn"
								on:click={() => sendComment(commenting)}
								>Envoyer</button
							> -->
							</div>
						{:else}
							<h6 id="modal-mode-selection" class="modal-title">
								Quels modèles voulez-vous comparer ?
							</h6>
							<p>Sélectionnez les modèles à comparer (2 max.)</p>
							<div>
								<!-- <ModelsSelection
									{models}
									bind:custom_models_selection
								/> -->
								<div class="fr-mt-2w">
									<button
										aria-controls="modal-mode-selection"
										class="btn">Annuler</button
									>
									<button
										aria-controls="modal-mode-selection"
										class="btn purple-btn float-right"
										>Envoyer</button
									>
								</div>
								<!-- <button
							aria-controls="modal-mode-selection"
							class="btn purple-btn"
							on:click={() => sendComment(commenting)}
							>Envoyer</button
						> -->
							</div>{/if}
					</div>
				</div>
			</div>
		</div>
	</div>
</dialog>

<style>
	.mode-selection-btn {
		--hover-tint: transparent;
		--active-tint: transparent;
		--focus-tint: transparent;
		display: flex;
		border-radius: 0.5em;
		border: 1px solid #e5e5e5 !important;
		flex-direction: row;
		padding: 0.5em;
		min-width: 260px;
		text-align: left;
		font-weight: 600;
		font-size: 0.875em;
		color: #3a3a3a !important;
	}
	.mode-selection-btn svg {
		flex-grow: 0;
	}
	.mode-selection-btn span {
		margin-left: 0.5em;
		flex-grow: 1;
	}

	.float-right {
		float: right;
	}

	.fr-modal__content {
		margin-bottom: 1em !important;
	}

	.fr-btn--close {
		color: #6a6af4 !important;
	}

	.fr-btn--close::after {
		background-color: #6a6af4 !important;
	}

	h6 {
		font-size: 1.125em;
	}
</style>
