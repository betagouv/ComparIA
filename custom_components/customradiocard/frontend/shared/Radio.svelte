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
	class="custom-card"
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
		/* height: 150px !important; */
		display: flex;
		align-items: left;
		transition: var(--button-transition);
		cursor: pointer;
		box-shadow: var(--checkbox-label-shadow);
		border: 1px solid #E5E5E5 !important;
		border-radius: 0.5rem;
		background-color: white;
		color: var(--grey-200-850);
		    /* color: var(--grey-50-1000); */
		font-weight: var(--checkbox-label-text-weight);
		font-size: 1rem;
		line-height: var(--line-md);
	}

	/* label:hover {
		background: var(--checkbox-label-background-fill-hover);
	} */

	label.selected, label:focus {
		/* --blue-france-975-75: #f5f5fe; */

		/* --blue-france-main-525: #6a6af4; */
		outline: 2px solid var(--blue-france-main-525);
		/* color: var(--blue-france-main-525); */
	}

	label > * + * {
		margin-left: var(--size-2);
	}


	input[type="radio"] {
		display: none;
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
