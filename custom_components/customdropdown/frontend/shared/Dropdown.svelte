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

	// Hardcoded options
	const choices = [
		{
			value: "random",
			label: "Aléatoire",
			icon: "random-icon", // Replace with your icon class or SVG
			description: "Deux modèles choisis au hasard parmi toute la liste",
		},
		{
			value: "small-models",
			label: "Économe",
			icon: "eco-icon", // Replace with your icon class or SVG
			description:
				"Minimisez votre impact environnemental avec deux petits modèles",
		},
		{
			value: "big-vs-small",
			label: "Petit contre grand",
			icon: "compare-icon", // Replace with your icon class or SVG
			description:
				"Comparez les performances d’un petit modèle contre un grand",
		},
		{
			value: "custom",
			label: "Sélection manuelle",
			icon: "manual-icon", // Replace with your icon class or SVG
			description:
				"Sélectionnez vous-même jusqu’à deux modèles à comparer",
		},
	];

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
				class="custom-card"
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
				<span class="icon">
					<!-- Replace this with actual icon code or an icon library like Font Awesome -->
					<i class={icon}></i>
				</span>
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
