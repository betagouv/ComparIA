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
		border: 2px solid #6a6af4;
		/* border: 2px solid var(--blue-france-main-525); */
	}

	label {
		border-radius: 0.5em;
		border: 0.5px solid #e5e5e5;
		display: flex;
		flex-direction: row;
	}

	input[type="radio"] {
		position: fixed;
		opacity: 0;
		pointer-events: none;
	}
	p {
		color: #666666;
		font-size: 0.875em;
	}

	label div {
		flex-grow: 1;
	}

	strong {
		font-size: 0.875em;
		color: #3a3a3a;
	}

	.icon {
		flex-grow: 0;
	}
</style>
