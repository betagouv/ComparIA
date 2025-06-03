<script context="module">
	let id = 0;
</script>

<script lang="ts">
	import { createEventDispatcher } from "svelte";
	export let display_value: string;
	export let internal_value: string;
	export let disabled = false;
	export let selected: string | null = null;

	const dispatch = createEventDispatcher<{ input: string }>();
	let is_selected = false;

	// This function will handle the update of the selected state
	async function handle_input(
		selected: string | null,
		internal_value: string,
	): Promise<void> {
		is_selected = selected === internal_value;
		if (is_selected) {
			dispatch("input", internal_value);
		}
	}

	$: handle_input(selected, internal_value);

	// Handle label click or space/enter key press to toggle selection
	function handleSelection() {
		// If we don't want to reshuffle
		// if (disabled || selected === internal_value) return;
		if (disabled) return;
		selected = internal_value;
		dispatch("input", internal_value);
	}

	// Handle keydown event (Space or Enter)
	function handleKeyDown(event: KeyboardEvent) {
		if (event.key === " " || event.key === "Enter") {
			event.preventDefault(); // Prevent page scroll with spacebar
			handleSelection(); // Trigger selection when space or enter is pressed
		}
	}
</script>

<!-- svelte-ignore a11y-no-noninteractive-element-to-interactive-role -->
<label
	class:disabled
	class:selected={is_selected}
	class="custom-card"
	data-testid="{internal_value}-radio-label"
	tabindex="0"
	role="radio"
	aria-checked={is_selected}
	on:click={handleSelection}
	on:keydown={handleKeyDown}
>
	<input
		{disabled}
		type="radio"
		name="radio-{++id}"
		value={internal_value}
		aria-checked={is_selected}
		bind:group={selected}
		aria-hidden="true"
	/>
	{@html display_value}
</label>

<style>
	label {
		padding: 1rem 1rem 1rem 1rem !important;
		display: flex;
		align-items: left;
		transition: var(--button-transition);
		cursor: pointer;
		box-shadow: var(--checkbox-label-shadow);
		outline: 1px solid #e5e5e5;
		border-radius: 0.5rem;
		background-color: white;
		color: var(--grey-200-850);
		font-weight: var(--checkbox-label-text-weight);
		font-size: 1rem;
		line-height: var(--line-md);
	}

	label.selected,
	label:active {
		outline-offset: 0 !important;
		outline: 2px solid var(--blue-france-main-525) !important;
	}

	label > * + * {
		margin-left: var(--size-2);
	}

	input[type="radio"] {
		display: none; /* Hide the actual radio button */
	}

	input[disabled],
	.disabled {
		cursor: not-allowed;
	}
	
	label img {
		height: fit-content;
	}
</style>
