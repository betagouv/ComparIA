<script context="module">
	let id = 0;
</script>

<script lang="ts">
	import { createEventDispatcher } from "svelte";
	export let display_value: string;
	export let internal_value: string | number;
	export let disabled = false;
	export let selected: string | null = null;

	const dispatch = createEventDispatcher<{ input: string | number }>();
	let is_selected = false;

	async function handle_input(
		selected: string | null,
		internal_value: string | number
	): Promise<void> {
		is_selected = selected === internal_value;
		if (is_selected) {
			dispatch("input", internal_value);
		}
	}

	$: handle_input(selected, internal_value);
</script>

<label
	class:disabled
	class:selected={is_selected}
	class="fr-card fr-col-5 fr-col-md-3 fr-mx-1w fr-my-1w"
	data-testid="{internal_value}-radio-label"
	>
	<input
		{disabled}
		type="radio"
		name="radio-{++id}"
		value={internal_value}
		aria-checked={is_selected}
		bind:group={selected}
	/>
	{@html display_value}
</label>

<style>
	label {
		padding: 1.5rem 1rem 1.5rem 1.5rem !important;
		height: 150px !important;
		display: flex;
		align-items: left;
		transition: var(--button-transition);
		cursor: pointer;
		box-shadow: var(--checkbox-label-shadow);
		border: var(--checkbox-label-border-width) solid
			var(--checkbox-label-border-color);
		border-radius: var(--button-small-radius);
		background: var(--checkbox-label-background-fill);
		color: var(--checkbox-label-text-color);
		font-weight: var(--checkbox-label-text-weight);
		font-size: var(--checkbox-label-text-size);
		line-height: var(--line-md);
	}

	label:hover {
		background: var(--checkbox-label-background-fill-hover);
	}
	label:focus {
		background: var(--checkbox-label-background-fill-focus);
	}

	label.selected {
		background-color: var(--background-alt-grey) !important;
		/* color: var(--checkbox-label-text-color-selected); */
	}

	label > * + * {
		margin-left: var(--size-2);
	}

	input[type="radio"] {
		display: none !important;
		/* --ring-color: transparent;
		position: relative;
		box-shadow: var(--checkbox-shadow);
		border: var(--checkbox-border-width) solid var(--checkbox-border-color);
		border-radius: var(--radius-full);
		background-color: var(--checkbox-background-color);
		line-height: var(--line-sm); */
	}

	input:checked,
	input:checked:hover {
		border-color: var(--checkbox-border-color-selected);
		background-image: var(--radio-circle);
		background-color: var(--checkbox-background-color-selected);
	}

	input:hover {
		border-color: var(--checkbox-border-color-hover);
		background-color: var(--checkbox-background-color-hover);
	}

	input:focus {
		border-color: var(--checkbox-border-color-focus);
		background-color: var(--checkbox-background-color-focus);
	}

	input:checked:focus {
		border-color: var(--checkbox-border-color-focus);
		background-image: var(--radio-circle);
		background-color: var(--checkbox-background-color-selected);
	}

	input[disabled],
	.disabled {
		cursor: not-allowed;
	}
</style>
