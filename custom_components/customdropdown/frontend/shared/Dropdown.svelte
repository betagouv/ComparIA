<script lang="ts">
	import { createEventDispatcher } from "svelte";
	import type { SelectData } from "@gradio/utils";

	type Item = string | number;

	export let value: Item | Item[] | undefined = undefined;
	export let disabled = false;

	let selected_index: number | null = null;
	const dispatch = createEventDispatcher<{
		select: SelectData;
	}>();
	export var choices;

	// Handle option selection
	function handle_option_selected(index: number): void {
		selected_index = index;
		value = choices[index].value;
		dispatch("select", {
			index: selected_index,
			value: choices[selected_index].value,
			selected: true,
		});
	}

	$: {
		if (
			selected_index !== null &&
			choices &&
			choices.length > selected_index
		) {
			value = choices[selected_index].value;
		}
	}
</script>

<div>
	{#each choices as { value, label, _alt_label, icon, description }, index}
		<!-- svelte-ignore a11y-no-noninteractive-element-to-interactive-role -->
		<!-- svelte-ignore a11y-click-events-have-key-events -->
		<label
			class:selected={selected_index === index}
			class:disabled
			data-testid={`radio-label-${value}`}
			tabindex="0"
			role="radio"
			aria-checked={selected_index === index ? "true" : "false"}
			on:click={() => handle_option_selected(index)}
		>
			<input
				type="radio"
				name="radio-options"
				{value}
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
