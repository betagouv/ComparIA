<script lang="ts">
	import { createEventDispatcher } from "svelte";
	import type { ModeAndPromptData, Model } from "./utils.js";
	// export let handle_option_selected;
	// TODO: might need to refacto w/ mapfilter func for only choice + custom_models_selection + models
	// export let mode: "random" | "custom" | "big-vs-small" | "small-models" =
	// 	"random";
	// export let prompt_value: string = ""; // Initialize as an empty string by default
	export let custom_models_selection: string[] = []; // Default to an empty list
	export let models: Model[] = [];
	// Combine all into one value object based on mode and other properties
	// export let value: {
	// 	prompt_value: string;
	// 	mode: "random" | "custom" | "big-vs-small" | "small-models";
	// 	custom_models_selection: Item[];
	// } = {
	// 	prompt_value: "",
	// 	mode: "random",
	// 	custom_models_selection: [],
	// };
	export let disabled = false;

	// let selected_index: number | null = null;
	const dispatch = createEventDispatcher<{
		select: ModeAndPromptData;
		change: never;
	}>();
	export let toggle_model_selection: (id: string) => void;
	// export var choices;

	// $: {
	// 	if (
	// 		selected_index !== null &&
	// 		choices &&
	// 		choices.length > selected_index
	// 	) {
	// 		// value = choices[selected_index].value;
	// 		// value.mode = choices[selected_index].value;
	// 		mode = choices[selected_index].value;
	// 	}
	// }
</script>

<div class="models-grid">
	{#each models as { id, simple_name, icon_path, organisation, params, total_params, friendly_size, distribution }, index}
		<!-- svelte-ignore a11y-no-noninteractive-element-to-interactive-role -->
		<!-- svelte-ignore a11y-click-events-have-key-events -->
		<label
			class:selected={custom_models_selection.includes(id)}
			class:disabled={disabled ||
				(!custom_models_selection.includes(id) &&
					custom_models_selection.length == 2)}
			data-testid={`radio-label-${id}`}
			tabindex="0"
			role="radio"
			aria-checked={custom_models_selection.includes(id)
				? "true"
				: "false"}
		>
			<input
				type="radio"
				name="radio-options"
				value={id}
				data-index={index}
				aria-checked={custom_models_selection.includes(id)}
				disabled={disabled ||
					(!custom_models_selection.includes(id) &&
						custom_models_selection.length == 2)}
				on:click={(e) => {
					toggle_model_selection(id);
					e.stopPropagation();
				}}
			/>
			<div>
				<span class="icon">
					<img
						src="../assets/orgs/{icon_path}"
						alt={organisation}
						width="20"
						class="inline"
					/>
				</span>&nbsp;{organisation}/<strong>{simple_name}</strong>
			</div>
			<p>
				<span
					class:fr-badge--info={distribution == "api-only"}
					class:fr-badge--yellow-tournesol={distribution ==
						"open-weights"}
					class="fr-badge fr-badge--sm fr-badge--no-icon fr-mr-1v fr-mb-1v"
				>
					{distribution == "api-only"
						? "Propriétaire"
						: "Open weights"}
				</span>
				<span class="fr-badge fr-badge--no-icon fr-mr-1v fr-mb-1v">
					{#if distribution === "api-only"}
						Taille estimée ({friendly_size})
					{:else}
						{typeof params === "number" ? params : total_params} mds
						paramètres
					{/if}</span
				>
			</p>
		</label>
	{/each}
</div>

<style>
	.models-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
	}

	@media (min-width: 48em) {
		.models-grid {
			grid-template-columns: 1fr 1fr 1fr;
		}
	}
	label.selected,
	/* label:not([disabled]):active { */
	label:active,
	label:focus {
		outline: 2px solid #6a6af4 !important;
		/* border: 2px solid var(--blue-france-main-525); */
	}
	label.disabled,
	label.disabled:active,
	label.disabled:focus {
		filter: grayscale(100%);
		outline: 0.5px solid #ccc !important;
	}
	label {
		border-radius: 0.5em;
		outline: 0.5px solid #e5e5e5;
		display: grid;
		padding: 1em;
		align-items: center;
		/* grid-template-columns: auto 1fr; */
		margin: 1em;
	}

	label .icon {
		padding: 0 0.5em 0 0.5em;
	}

	input[type="radio"],
	input[type="radio"]:disabled {
		position: fixed;
		opacity: 0 !important;
		pointer-events: none;
	}
	/* p {
		color: #666666 !important;
		font-size: 0.875em !important;
	} */
	strong {
		font-size: 0.875em;
		color: #3a3a3a;
	}
</style>
