<script context="module" lang="ts">
	export { default as BaseDropdown } from "./shared/Dropdown.svelte";
</script>

<script lang="ts">
	import type { Gradio, KeyUpData, SelectData } from "@gradio/utils";
	import Dropdown from "./shared/Dropdown.svelte";
	import ModelsSelection from "./shared/ModelsSelection.svelte";
	import { Block } from "@gradio/atoms";
	import type { LoadingStatus } from "@gradio/statustracker";
	import TextBox from "./shared/Textbox.svelte";
	import ChevronBas from "./shared/chevron-bas.svelte";
	import { fade } from "svelte/transition";

	// import { dsfr } from "@gouvfr/dsfr";

	import type { ModeAndPromptData, Model } from "./shared/utils.ts";

	export let never_clicked: boolean = true;
	export let models: Model[] = [];
	export let elem_id = "";
	export let elem_classes: string[] = [];
	export let visible = true;
	export let disabled = false;
	type Mode =
		| "random"
		| "custom"
		| "big-vs-small"
		| "small-models"
		| "reasoning";
	export let mode: Mode = "random";
	export let prompt_value: string = ""; // Initialize as an empty string by default
	export let custom_models_selection: string[] = []; // Default to an empty list

	// Prompt value
	// export let value: string = ""
	// Combine all into one value object based on mode and other properties
	export let value: {
		prompt_value: string;
		mode: Mode;
		custom_models_selection: string[];
	} = {
		prompt_value: "",
		mode: "random",
		custom_models_selection: [],
	};
	import Glass from "./shared/glass.svelte";
	import Leaf from "./shared/leaf.svelte";
	import Ruler from "./shared/ruler.svelte";
	import Brain from "./shared/brain.svelte";
	import Dice from "./shared/dice.svelte";

	type Choice = {
		value: Mode;
		label: string;
		alt_label: string;
		icon: any;
		description: string;
	};
	export const choices: Choice[] = [

	{
			value: "random",
			label: "Aléatoire",
			alt_label: "Modèles aléatoires",
			icon: Dice, // Replace with your icon class or SVG
			description: "Deux modèles tirés au hasard dans la liste",
		},
		{
			value: "custom",
			label: "Sélection manuelle",
			alt_label: "Sélection manuelle",
			icon: Glass, // Replace with your icon class or SVG
			description: "",
		},
		{
			value: "small-models",
			label: "Frugal",
			alt_label: "Modèles frugaux",

			icon: Leaf, // Replace with your icon class or SVG
			description:
				"Deux modèles tirés au hasard parmi ceux de plus petite taille",
		},
		{
			value: "big-vs-small",
			label: "David contre Goliath",
			alt_label: "David contre Goliath",
			icon: Ruler, // Replace with your icon class or SVG
			description:
				"Un petit modèle contre un grand, les deux tirés au hasard",
		},
		{
			value: "reasoning",
			label: "Raisonnement",
			alt_label: "Modèles avec raisonnement",
			icon: Brain, // Replace with your icon class or SVG
			description:
				"Deux modèles tirés au hasard parmi ceux optimisés pour des tâches complexes",
		},
	];

	export let container = true;
	export let scale: number | null = null;
	export let min_width: number | undefined = undefined;
	// export let allow_custom_value = false;
	// FIXME: types for events
	export let gradio: Gradio<{
		change: ModeAndPromptData;
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
	export let value_is_output = false;
	export let lines: number = 4;
	export let show_custom_models_selection: boolean = false;
	export let max_lines: number;
	// export let scale: number | null = null;
	// export let min_width: number | undefined = undefined;
	export let rtl = false;
	export let text_align: "left" | "right" | undefined = undefined;
	export let autofocus = false;
	export let autoscroll = true;
	var first_model_name = "Aléatoire";
	var second_model_name = "Aléatoire";
	var first_model_icon_path = null;
	var second_model_icon_path = null;

	export let interactive: boolean;
	// random by default
	var choice: Choice = choices[0];

	// Handle mode selection
	function handle_option_selected(index: number): void {
		console.log("handle_option_selected");
		if (index !== null && choices && choices.length > index) {
			// value = choices[selected_index].value;
			// value.mode = choices[selected_index].value;

			mode = choices[index].value;
			if (mode != value["mode"]) {
				value["mode"] = mode;
				// Don't tell backend to switch to custom if no custom_models_selection yet
				if (
					!(mode == "custom" && custom_models_selection.length == 0)
				) {
					gradio.dispatch("select", {
						mode: mode,
						custom_models_selection: custom_models_selection,
						prompt_value: prompt_value,
					});
				}
				choice = choices.find((item) => item.value === mode);
			}
		}
		if (mode == "custom") {
			show_custom_models_selection = true;
		}
	}

	function toggle_model_selection(id) {
		// Toggle if already added or to add/delete
		if (!custom_models_selection.includes(id)) {
			if (custom_models_selection.length < 2) {
				console.log("adding " + id);
				custom_models_selection.push(id);
			}
		} else {
			console.log("removing " + id);
			var index = custom_models_selection.indexOf(id);
			custom_models_selection.splice(index, 1);
		}

		value["custom_models_selection"] = custom_models_selection;
		first_model_name =
			custom_models_selection[0] !== undefined
				? models.find(
						(model) => model["id"] === custom_models_selection[0],
					).simple_name
				: "Aléatoire";

		first_model_icon_path =
			custom_models_selection[0] !== undefined
				? models.find(
						(model) => model["id"] === custom_models_selection[0],
					).icon_path
				: null;

		second_model_name =
			custom_models_selection[1] !== undefined
				? models.find(
						(model) => model["id"] === custom_models_selection[1],
					).simple_name
				: "Aléatoire";

		second_model_icon_path =
			custom_models_selection[1] !== undefined
				? models.find(
						(model) => model["id"] === custom_models_selection[1],
					).icon_path
				: null;

		gradio.dispatch("select", {
			mode: mode,
			custom_models_selection: custom_models_selection,
			prompt_value: prompt_value,
		});

		// If clicked on second model, close model selection modal
		if (custom_models_selection.length == 2) {
			const modeSelectionModal = document.getElementById("modal-mode-selection")
			// maybe add a 500 ms delay
			window.dsfr(modeSelectionModal).modal.conceal()
		}
	}

	// Handle prompt value update from backend
	$: {
		if (value_is_output) {
			prompt_value = value["prompt_value"];
		} else {
			if (value["prompt_value"] != prompt_value) {
				value["prompt_value"] = prompt_value;
			}
		}
	}
	var alt_label: string = "Sélection des modèles";
	$: if (
		(mode == "custom" && custom_models_selection.length < 1) ||
		(mode == "random" && never_clicked)
	) {
		alt_label = "Sélection des modèles";
	} else {
		alt_label = choice.alt_label;
	}
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
	<h3 class="text-center text-grey-200 fr-mt-md-12w fr-mb-md-7w fr-my-5w">
		Comment puis-je vous aider aujourd'hui ?
	</h3>
	<div class="grid">
		<div class="first-textbox fr-mb-3v">
			<TextBox
				{disabled}
				bind:value={prompt_value}
				bind:value_is_output
				{elem_id}
				{elem_classes}
				{visible}
				{lines}
				{rtl}
				{text_align}
				max_lines={!max_lines ? lines + 1 : max_lines}
				placeholder="Écrivez votre premier message ici"
				{autofocus}
				{autoscroll}
				on:change={() =>
					gradio.dispatch("change", {
						prompt_value: prompt_value,
						mode: mode,
						custom_models_selection: custom_models_selection,
					})}
				on:submit={() => {
					gradio.dispatch("submit", {
						prompt_value: prompt_value,
						mode: mode,
						custom_models_selection: custom_models_selection,
					});
					disabled = true;
				}}
			/>
		</div>

		<div class="selections">
			<button
				class="mode-selection-btn fr-mb-md-0 fr-mb-1w fr-mr-3v"
				data-fr-opened="false"
				{disabled}
				aria-controls="modal-mode-selection"
				on:click={() => {
					never_clicked = false;
					show_custom_models_selection = false;
				}}
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
				<span class="label"> {alt_label}</span><span class="chevron"
					><svelte:component this={ChevronBas} />
				</span></button
			>
			{#if mode == "custom" && custom_models_selection.length > 0}
				<button
					{disabled}
					class="model-selection fr-mb-md-0 fr-mb-1w"
					data-fr-opened="false"
					aria-controls="modal-mode-selection"
				>
					<img
						src="../assets/orgs/{first_model_icon_path}"
						alt={first_model_name}
						width="20"
						class="inline"
					/>&nbsp;
					{first_model_name}
					<strong class="versus">&nbsp;vs.&nbsp;</strong>
					{#if second_model_icon_path != null}
						<img
							src="../assets/orgs/{second_model_icon_path}"
							alt={second_model_name}
							width="20"
							class="inline"
						/>&nbsp;
					{/if}
					{second_model_name}</button
				>
			{/if}
		</div>
		<input
			type="submit"
			class="submit-btn purple-btn btn"
			disabled={prompt_value == "" || disabled}
			on:click={() => {
				gradio.dispatch("submit", {
					prompt_value: prompt_value,
					mode: mode,
					custom_models_selection: custom_models_selection,
				});
				disabled = true;
			}}
			value="Envoyer"
		/>
	</div>
</Block>
<dialog
	aria-labelledby="modal-mode-selection"
	id="modal-mode-selection"
	class="fr-modal"
>
	<div class="fr-container fr-container--fluid fr-container-md">
		<div class="fr-grid-row fr-grid-row--center">
			<div
				class="fr-col-12"
				class:fr-col-md-10={show_custom_models_selection}
				class:fr-col-md-5={!show_custom_models_selection}
			>
				<div class="fr-modal__body">
					<div class="fr-modal__header">
						<button
							class="fr-btn--close fr-btn"
							title="Fermer la fenêtre modale"
							aria-controls="modal-mode-selection">Fermer</button
						>
					</div>
					<div class="fr-modal__content fr-pb-4w">
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
									{handle_option_selected}
									{choices}
									bind:mode
									on:select={(e) =>
										gradio.dispatch("select", e.detail)}
									disabled={!interactive}
								/>
							</div>
						{:else}
							<div in:fade>
								<h6
									id="modal-mode-selection"
									class="modal-title"
								>
									Quels modèles voulez-vous comparer ?
									<span class="text-purple fr-ml-2w">
										{custom_models_selection.length}/2
										modèles
									</span>
								</h6>
								<p class="fr-mb-2w">
									Si vous n’en choisissez qu’un, le second
									sera sélectionné de manière aléatoire
								</p>
								<div>
									<ModelsSelection
										{models}
										bind:custom_models_selection
										{toggle_model_selection}
									/>
									<div class="fr-mt-2w">
										<button
											class="btn fr-mb-md-0 fr-mb-1w"
											on:click={() =>
												(show_custom_models_selection = false)}
											>Retour</button
										>
										<button
											aria-controls="modal-mode-selection"
											class="btn purple-btn float-right"
											on:click={() =>
												gradio.dispatch("select", {
													prompt_value: prompt_value,
													mode: mode,
													custom_models_selection:
														custom_models_selection,
												})}>Valider</button
										>
									</div>
								</div>
							</div>
						{/if}
					</div>
				</div>
			</div>
		</div>
	</div>
</dialog>

<style>
	.versus {
		font-size: 1.125rem;

		line-height: 0 !important;
	}

	.chevron {
		line-height: 0;
	}

	.text-purple {
		color: #6a6af4;
	}

	.mode-selection-btn {
		--hover-tint: transparent;
		--active-tint: transparent;
		--focus-tint: transparent;
		display: flex;
		width: 100%;
		border-radius: 0.5em;
		border: 1px solid #e5e5e5 !important;
		flex-direction: row;
		padding: 0.5em;
		text-align: left;
		font-weight: 500;
		font-size: 0.875em;
		color: #3a3a3a !important;
		background-color: white !important;
	}

	.model-selection {
		align-items: center;
		width: 100%;
		--hover-tint: transparent;
		--active-tint: transparent;
		--focus-tint: transparent;
		display: flex;
		border-radius: 0.5em;
		border: 1px solid #e5e5e5 !important;
		flex-direction: row;
		padding: 0.5em;

		text-align: left;
		font-weight: 500;
		font-size: 0.875em !important;
		color: #3a3a3a !important;
		background-color: white !important;
		max-height: 40px;
	}

	.mode-selection-btn svg {
		flex-grow: 0;
	}
	.mode-selection-btn .label {
		margin-left: 0.5em;
		flex-grow: 1;
		font-size: 0.875em;
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

	.grid {
		display: grid;
		/* grid-template-columns: 1fr 1fr auto; */
	}
	.first-textbox {
		order: 1;
	}
	.mode-selection-btn {
		order: 0;
	}
	.submit-btn {
		order: 2;
		width: 100% !important;
	}
	/* .fr-modal__content { */
	.fr-modal__body {
		overflow-y: scroll;
	}

	@media (min-width: 48em) {
		.first-textbox,
		.mode-selection-btn {
			order: initial;
		}
		.submit-btn {
			width: 8.25rem !important;
		}
		.grid {
			grid-template-areas: "text text" "left right";
		}
		.first-textbox {
			grid-area: text;
		}

		.selections {
			grid-area: left;
			display: flex;
		}
		.mode-selection-btn {
			width: 260px;
		}
		.model-selection {
			width: fit-content;
		}

		.submit-btn {
			grid-area: right;
			justify-self: right;
		}
	}
</style>
