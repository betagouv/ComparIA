<script lang="ts">
	import { createEventDispatcher, afterUpdate } from "svelte";
	import type { SelectData, KeyUpData } from "@gradio/utils";
	import { handle_change } from "./utils";

	type Item = string | number;

	export let value: Item | Item[] | undefined = undefined;
	let old_value: typeof value = undefined;
	export let value_is_output = false;
	let choices = [
		{
			value: "random",
			label: "Aléatoire",
			description: "Deux modèles choisis au hasard parmi toute la liste",
		},
		{
			value: "eco",
			label: "Économe",
			description:
				"Minimisez votre impact environnemental avec deux petits modèles",
		},
		{
			value: "small_vs_large",
			label: "Petit contre grand",
			description:
				"Comparez les performances d’un petit modèle contre un grand",
		},
		{
			value: "manual",
			label: "Sélection manuelle",
			description:
				"Sélectionnez vous-même jusqu’à deux modèles à comparer",
		},
	];
	let old_choices: typeof choices;
	export let disabled = false;
	export let allow_custom_value = false;

	let filter_input: HTMLElement;

	let show_options = false;
	let choices_names: string[];
	let choices_values: (string | number)[];
	let input_text = "";
	let old_input_text = "";
	let initialized = false;

	// All of these are indices with respect to the choices array
	let filtered_indices: number[] = [];
	let active_index: number | null = null;
	// selected_index is null if allow_custom_value is true and the input_text is not in choices_names
	let selected_index: number | null = null;
	let old_selected_index: number | null;

	const dispatch = createEventDispatcher<{
		change: string | undefined;
		input: undefined;
		select: SelectData;
		blur: undefined;
		focus: undefined;
		key_up: KeyUpData;
	}>();

	// Setting the initial value of the dropdown
	if (value) {
		old_selected_index = choices
			.map((c) => c.value)
			.indexOf(value as string);
		selected_index = old_selected_index;
		if (selected_index === -1) {
			old_value = value;
			selected_index = null;
		} else {
			input_text = choices[selected_index].label;
			old_value = value;
		}
		set_input_text();
	}

	// Watch for changes in the selected index
	$: {
		if (
			selected_index !== old_selected_index &&
			selected_index !== null &&
			initialized
		) {
			input_text = choices[selected_index].label;
			value = choices[selected_index].value;
			old_selected_index = selected_index;
			dispatch("select", {
				index: selected_index,
				value: choices[selected_index].value,
				selected: true,
			});
		}
	}

	// Handle changes to the value
	$: if (JSON.stringify(old_value) !== JSON.stringify(value)) {
		set_input_text();
		handle_change(dispatch, value, false); // assuming value_is_output is false
		old_value = value;
	}

	// Set choice names and values
	function set_choice_names_values(): void {
		choices_names = choices.map((c) => c.label);
		choices_values = choices.map((c) => c.value);
	}

	$: choices, set_choice_names_values();

	// Filter choices based on input text
	$: {
		if (choices !== old_choices) {
			if (!allow_custom_value) {
				set_input_text();
			}
			old_choices = choices;
			if (!allow_custom_value && choices.length > 0) {
				active_index = filtered_indices[0];
			}
			if (is_browser && filter_input === document.activeElement) {
				show_options = true;
			}
		}
	}

	$: if (JSON.stringify(old_value) !== JSON.stringify(value)) {
		set_input_text();
		handle_change(dispatch, value, value_is_output);
		old_value = value;
	}

	const is_browser = typeof window !== "undefined";

	$: {
		if (choices !== old_choices) {
			if (!allow_custom_value) {
				set_input_text();
			}
			old_choices = choices;
			if (!allow_custom_value && choices.length > 0) {
				active_index = filtered_indices[0];
			}
			if (is_browser && filter_input === document.activeElement) {
				show_options = true;
			}
		}
	}

	$: {
		if (input_text !== old_input_text) {
			old_input_text = input_text;
			if (!allow_custom_value && choices.length > 0) {
				active_index = filtered_indices[0];
			}
		}
	}

	function set_input_text(): void {
		set_choice_names_values();
		if (
			value === undefined ||
			(Array.isArray(value) && value.length === 0)
		) {
			input_text = "";
			selected_index = null;
		} else if (choices_values.includes(value as string)) {
			input_text = choices_names[choices_values.indexOf(value as string)];
			selected_index = choices_values.indexOf(value as string);
		} else if (allow_custom_value) {
			input_text = value as string;
			selected_index = null;
		} else {
			input_text = "";
			selected_index = null;
		}
		old_selected_index = selected_index;
	}

	function handle_option_selected(e: any): void {
		selected_index = parseInt(e.detail.target.dataset.index);
		if (isNaN(selected_index)) {
			// This is the case when the user clicks on the scrollbar
			selected_index = null;
			return;
		}
		show_options = false;
		active_index = null;
		filter_input.blur();
	}

	afterUpdate(() => {
		value_is_output = false;
		initialized = true;
	});
</script>

<div class="wrap">
	<div class="wrap-inner">
		{#each choices as { value, label, description }, index}
			<!-- svelte-ignore a11y-no-noninteractive-element-to-interactive-role -->
			<!-- svelte-ignore a11y-click-events-have-key-events -->
			<label
				class="custom-card"
				class:selected={selected_index === index}
				class:disabled
				data-testid={`radio-label-${value}`}
				tabindex="0"
				role="radio"
				aria-checked={selected_index === index ? "true" : "false"}
				on:click={() =>
					handle_option_selected({
						detail: { target: { dataset: { index } } },
					})}
			>
				<input
					type="radio"
					name="radio-options"
					{value}
					bind:group={selected_index}
					data-index={index}
					aria-checked={selected_index === index}
					{disabled}
				/>
				<span>{label}</span>
				<p>{description}</p>
			</label>
		{/each}
	</div>
</div>

<style>
	.wrap {
		position: relative;
		border-radius: var(--input-radius);
		background: var(--input-background-fill);
	}

	.wrap:focus-within {
		box-shadow: var(--input-shadow-focus);
		border-color: var(--input-border-color-focus);
		background: var(--input-background-fill-focus);
	}

	.wrap-inner {
		display: flex;
		position: relative;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--checkbox-label-gap);
		padding: var(--checkbox-label-padding);
		height: 100%;
	}

	input {
		margin: var(--spacing-sm);
		outline: none;
		border: none;
		background: inherit;
		width: var(--size-full);
		color: var(--body-text-color);
		font-size: var(--input-text-size);
		height: 100%;
	}

	input:disabled {
		-webkit-text-fill-color: var(--body-text-color);
		-webkit-opacity: 1;
		opacity: 1;
		cursor: not-allowed;
	}
</style>
