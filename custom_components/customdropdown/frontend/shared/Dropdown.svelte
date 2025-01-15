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
</script>

<div class="wrap">
	<div class="wrap-inner">
		{#each choices as { value, label, description, icon }, index}
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
					bind:group={selected_index}
					data-index={index}
					aria-checked={selected_index === index}
					{disabled}
				/>
				<svelte:component this={icon} />
				<div><strong>{label}</strong>
				<p>{description}</p></div>
			</label>
		{/each}
	</div>
</div>

<style>
	label.selected, 
	label:active {
		outline: 2px solid var(--blue-france-main-525); 
		outline-offset: 0 !important;

	}
	input {
		list-style: none;
	}
	p {
		color: #666666;
		font-size: 0.875em;
	}
	
	strong {
		font-size: 0.875em;
		color: #3A3A3A
	}
</style>
