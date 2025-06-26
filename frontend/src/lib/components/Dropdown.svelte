<script lang="ts">
	import type { Choice, Mode } from "$lib/utils-customdropdown";
	export let handle_option_selected: (index: number) => void;
	// TODO: might need to refacto w/ mapfilter func for only choice + custom_models_selection + models
	export let mode: Mode;
		
	export let disabled = false;

	export var choices: Choice[];

	import ChevronDroite from "./chevron-droite.svelte";

	function handleKeyDown(index: number, event: KeyboardEvent) {
		if (event.key === " " || event.key === "Enter") {
			event.preventDefault();
			handle_option_selected(index);
		}
	}
</script>

<div>
	{#each choices as { value, label, alt_label, icon, description }, index}
		<!-- svelte-ignore a11y-no-noninteractive-element-to-interactive-role -->
		<!-- svelte-ignore a11y-click-events-have-key-events -->
		<label
			class:selected={value === mode}
			class:disabled
			data-testid={`radio-label-${mode}`}
			tabindex="0"
			role="radio"
			aria-checked={value === mode ? "true" : "false"}
			on:click={() => handle_option_selected(index)}
			on:keydown={(e) => handleKeyDown(index,e)}
			aria-controls={value != "custom" ? "modal-mode-selection" : ""}
		>
			<input
				type="radio"
				name="radio-options"
				value={mode}
				data-index={index}
				aria-checked={value === mode}
				{disabled}
			/>
			<div class="icon">
				<svelte:component this={icon} />
			</div>
			<div class="description">
				<strong>{label}</strong>{#if value != "custom"}&nbsp;: {description}
				{:else}
				<span class="chevron-droite"><svelte:component this={ChevronDroite} /></span>
				{/if}
			</div>
		</label>
	{/each}
</div>

<style>
	label.selected,
	label:active,
	label:focus {
		outline: 2px solid #6a6af4 !important;
		/* border: 2px solid var(--blue-france-main-525); */
	}

	label {
		border-radius: 0.5em;
		outline: 1px solid #e5e5e5;
		display: grid;
		padding: 1em 0.5em;
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
	/* p {
		color: #666666 !important;
		font-size: 0.875em !important;
	} */
	.description {
		font-size: 0.875em;
		color: #3a3a3a;
	}
	
	.chevron-droite {
		line-height: 0;
		float: right;
		margin-right: 0.5em;
		position: relative;
	}
</style>
