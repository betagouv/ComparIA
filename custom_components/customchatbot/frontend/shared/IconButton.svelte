<script lang="ts">
	import { type ComponentType } from "svelte";
	export let Icon: ComponentType;
	export let label = "";
	export let show_label = false;
	export let pending = false;
	export let size: "small" | "large" | "medium" = "medium";
	export let padded = true;
	export let highlight = false;
	export let border = false;
	export let disabled = false;
	export let hasPopup = false;
	export let color = "var(--block-label-text-color)";
	export let transparent = false;
	$: _color = highlight ? "#6A6AF4" : color;
</script>

<button
	{disabled}
	on:click
	aria-label={label}
	aria-haspopup={hasPopup}
	title={label}
	class:pending
	class:padded
	class:border
	class:highlight
	class:transparent
>
	{#if show_label}<span>{label}</span>{/if}
	<div
		class:small={size === "small"}
		class:large={size === "large"}
		class:medium={size === "medium"}
	>
		<svelte:component this={Icon} />
	</div>
</button>

<style>
	button {
		display: flex;
		justify-content: center;
		align-items: center;
		gap: 1px;
		z-index: var(--layer-2);
		border-radius: 50%;
		color: var(--block-label-text-color);
		padding: 10px;
	}

	/* button:hover {
		background-color: var(--background-fill-secondary);
	} */
	button.border {
			border: 1px solid #E5E5E5 !important;
	}
	button.border.highlight {
			border: 1px solid #6A6AF4 !important;
			background-color: #F5F5FE !important;
	}

	button[disabled] {
		opacity: 0.5;
		box-shadow: none;
		background-color: #eee !important;
	}
	button.border.highlight[disabled] {
		border: 1px solid #606367 !important;

	}
	button[disabled]:hover {
		cursor: not-allowed;
	}

	.padded {
		background: var(--bg-color);
	}

	button:hover,
	button.highlight {
		cursor: pointer;
		color: #6A6AF4;
	}

	.padded:hover {
		color: var(--block-label-text-color);
	}

	span {
		padding: 0px 1px;
		font-size: 10px;
	}

	div {
		display: flex;
		align-items: center;
		justify-content: center;
		transition: filter 0.2s ease-in-out;
	}

	.small {
		width: 14px;
		height: 14px;
	}

	.medium {
		width: 20px;
		height: 20px;
	}

	.large {
		width: 22px;
		height: 22px;
	}

	.pending {
		animation: flash 0.5s infinite;
	}

	@keyframes flash {
		0% {
			opacity: 0.5;
		}
		50% {
			opacity: 1;
		}
		100% {
			opacity: 0.5;
		}
	}

	.transparent {
		background: transparent;
		border: none;
		box-shadow: none;
	}
</style>
