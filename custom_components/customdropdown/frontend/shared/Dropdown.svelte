<script lang="ts">
	import { createEventDispatcher } from "svelte";
	import type { ModeAndPromptData } from "./utils.ts";
	type Item = string | number;
	export let handle_option_selected;
	// TODO: might need to refacto w/ mapfilter func for only choice + custom_models_selection + models
	export let mode: "random" | "custom" | "big-vs-small" | "small-models" =
		"random";
	// export let prompt_value: string = ""; // Initialize as an empty string by default
	export let custom_models_selection: Item[] = []; // Default to an empty list
	export let models: Item[] = [];
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

	let selected_index: number | null = null;
	const dispatch = createEventDispatcher<{
		select: ModeAndPromptData;
		change: never;
	}>();
	export var choices;

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

<div>
	{#each choices as { mode, label, alt_label, icon, description }, index}
		<!-- svelte-ignore a11y-no-noninteractive-element-to-interactive-role -->
		<!-- svelte-ignore a11y-click-events-have-key-events -->
		<label
			class:selected={selected_index === index}
			class:disabled
			data-testid={`radio-label-${mode}`}
			tabindex="0"
			role="radio"
			aria-checked={selected_index === index ? "true" : "false"}
			on:click={() => handle_option_selected(index)}
		>
			<input
				type="radio"
				name="radio-options"
				value={mode}
				data-index={index}
				aria-checked={selected_index === index}
				{disabled}
			/>
			<div class="icon">
				<svelte:component this={icon} />
			</div>
			<div>
				<strong>{label}</strong>
				<p>{description}</p>
			</div>
		</label>
	{/each}
</div>

<style>
	label.selected,
	label:active {
		outline: 2px solid #6a6af4;
		/* border: 2px solid var(--blue-france-main-525); */
	}

	label {
		border-radius: 0.5em;
		outline: 0.5px solid #e5e5e5;
		display: grid;
		padding: 0.5em 1em 1em 0.25em;
		align-items: center;
		grid-template-columns: auto 1fr;
		margin: 0.75em 0;
	}

	label .icon {
		padding: 0 0.5em 0 0.5em;
	}

	input[type="radio"] {
		position: fixed;
		opacity: 0;
		pointer-events: none;
	}
	p {
		color: #666666 !important;
		font-size: 0.875em !important;
	}
	strong {
		font-size: 0.875em;
		color: #3a3a3a;
	}
</style>
