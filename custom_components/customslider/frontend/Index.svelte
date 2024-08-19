<script context="module">
	let _id = 0;
</script>

<script lang="ts">
	import type { Gradio } from "@gradio/utils";
	import { Block, BlockTitle } from "@gradio/atoms";
	import { StatusTracker } from "@gradio/statustracker";
	import type { LoadingStatus } from "@gradio/statustracker";
	import { afterUpdate } from "svelte";
	import { onMount } from "svelte";

	import "@gouvfr/dsfr/dist/scheme/scheme.css";
	import "@gouvfr/dsfr/dist/core/core.css";
	import "@gouvfr/dsfr/dist/component/form/form.css";
	import "@gouvfr/dsfr/dist/component/link/link.css";
	import "@gouvfr/dsfr/dist/component/button/button.css";
	import "@gouvfr/dsfr/dist/component/input/input.css";
	import "@gouvfr/dsfr/dist/component/range/range.css";

	export let gradio: Gradio<{
		change: never;
		input: never;
		release: number;
		clear_status: LoadingStatus;
	}>;
	export let elem_id = "";
	export let elem_classes: string[] = [];
	export let visible = true;
	export let extrema: string[] = [];
	export let range_labels: string[] = [];
	export let value = -100;
	export let label = gradio.i18n("slider.slider");
	export let info: string | undefined = undefined;
	// export let container = true;
	// export let scale: number | null = null;
	// export let min_width: number | undefined = undefined;
	export let minimum: number;
	export let maximum = 100;
	export let step: number;
	export let show_label: boolean;
	export let interactive: boolean;
	export let loading_status: LoadingStatus;
	export let value_is_output = false;

	let currentLabel: number;
	// TODO: set value from label click
	// let labelIndex: number;

	let rangeInput: HTMLInputElement;
	// let labelInput: HTMLInputElement;

	let sliderInteracted = false;

	const id = `range_id_${_id++}`;

	function handle_change(): void {
		gradio.dispatch("change");
		if (!value_is_output) {
			gradio.dispatch("input");
		}
	}
	afterUpdate(() => {
		value_is_output = false;
		setSlider();
	});

	function handle_release(e: MouseEvent): void {
		gradio.dispatch("release", value);
	}
	function handle_pointerdown(e: MouseEvent): void {
		sliderInteracted = true;
	}
	function clamp(): void {
		gradio.dispatch("release", value);
		value = Math.min(Math.max(value, minimum), maximum);
	}

	function setSlider(): void {
		setSliderRange();
		rangeInput.addEventListener("input", setSliderRange);
		// numberInput.addEventListener("input", setSliderRange);
	}
	function setSliderRange(): void {
		const dividend = Number(rangeInput.value) - Number(rangeInput.min);
		const divisor = Number(rangeInput.max) - Number(rangeInput.min);
		const h = divisor === 0 ? 0 : dividend / divisor;
		rangeInput.style.backgroundSize = h * 100 + "% 100%";
		setRangeLabel(h);
	}

	function setRangeLabel(h: number): void {
		if (range_labels && range_labels.length) {
			currentLabel = Math.round(Number((range_labels.length - 1) * h));
		}
	}
	$: disabled = !interactive;

	// When the value changes, dispatch the change event via handle_change()
	// See the docs for an explanation: https://svelte.dev/docs/svelte-components#script-3-$-marks-a-statement-as-reactive
	$: value, handle_change();

	// Reactive statement to update slider center
	// $: rangeInput.offsetWidth, rangeInput.style.setProperty('--slider-center', (rangeInput ? rangeInput.offsetWidth / 2 : 0).toString() + 'px');

	onMount(() => {
		const updateSliderCenter = () => {
			if (rangeInput) {
				rangeInput.style.setProperty(
					"--slider-center",
					`${rangeInput.offsetWidth / 2}px`,
				);
			}
		};

		updateSliderCenter(); // Initial update

		// Update on resize
		window.addEventListener("resize", updateSliderCenter);

		return () => {
			window.removeEventListener("resize", updateSliderCenter);
		};
	});
</script>

<div id={elem_id} class="custom-slider {visible ? '' : 'hide'} {elem_classes}">
	<StatusTracker
		autoscroll={gradio.autoscroll}
		i18n={gradio.i18n}
		{...loading_status}
		on:clear_status={() => gradio.dispatch("clear_status", loading_status)}
	/>
	<label class="fr-label" for={id}>
		{#if show_label}
			{label}
			<span class="fr-hint-text">{info}</span>
		{/if}
	</label>

	<div class="fr-range-group">
		<span class="fr-range__left" aria-hidden="true">{extrema[0]}</span>
		<div
			class="fr-range fr-range--step {sliderInteracted
				? 'interacted'
				: ''}"
			data-fr-js-range="true"
		>
			<span class="fr-range__output hide">{value}</span>
			<input
				type="range"
				{id}
				name={id}
				bind:value
				bind:this={rangeInput}
				min={minimum}
				max={maximum}
				{step}
				{disabled}
				on:pointerdown={handle_pointerdown}
				on:pointerup={handle_release}
				aria-label={`range slider for ${label}`}
			/>
			{#if range_labels.length != 0}
				{#each range_labels as range_label, labelIndex}
					<span
						class="fr-range__custom-label{currentLabel ==
							labelIndex && sliderInteracted
							? ' spotlight'
							: ''}"
						aria-hidden="true">{range_label}</span
					>
				{/each}
			{:else}
				<span class="fr-range__min" aria-hidden="true">{minimum}</span>
				<span class="fr-range__max" aria-hidden="true">{maximum}</span>
			{/if}
		</div>
		<span class="fr-range__right" aria-hidden="true">{extrema[1]}</span>
	</div>
</div>

<style>
	/* Style to center the thumb when not interacted */
	.fr-range[data-fr-js-range]:not(.interacted)
		input[type="range"]::-webkit-slider-thumb,
	.fr-range[data-fr-js-range]:not(.interacted)
		input[type="range"]::-moz-range-thumb {
		/* transform: translateX(calc(var(--slider-width)/2)); */
		transform: translateX(var(--slider-center));

		background-color: var(--background-default-grey-hover);
	}

	.fr-range-group {
		display: flex;
	}

	/* input[type="range"] {
		--slider-width: 100%;
	} */

	.fr-range[data-fr-js-range].interacted input[type="range"]::-webkit-slider-thumb,
	.fr-range[data-fr-js-range].interacted input[type="range"]::-moz-range-thumb {
		/* --hover: var(--background-raised-grey-hover);
		--active: var(--background-raised-grey-active);
		--hover: var(--background-default-grey-hover);
		--active: var(--background-default-grey-active);
		--idle: transparent; */
		/* Should be useless */
		transform: translateX(0);
		background-color: var(--background-action-high-blue-france) !important;
		border: 1px solid var(--border-action-high-blue-france) !important;
	}

	.fr-range--step[data-fr-js-range]::before,
	.fr-range--step[data-fr-js-range]::after,
	.fr-range[data-fr-js-range]::before,
	.fr-range--step[data-fr-js-range]::after {
		background-image: radial-gradient(
			circle at 2px 50%,
			var(--background-action-high-blue-france) 0,
			var(--background-action-high-blue-france) 2px,
			transparent 2px
		) !important;
		--progress-right: 0% !important;
	}

	.spotlight {
		font-weight: 500;
	}
	.fr-range__left,
	.fr-range__right {
		font-weight: 700;
		margin: 0 1rem;
		font-size: larger;
	}
	.spotlight,
	.fr-range__left,
	.fr-range__right {
		color: var(--text-action-high-blue-france);
		min-width: 5rem;
	}
	.fr-range--step[data-fr-js-range]::before,
	.fr-range--step[data-fr-js-range]::after {
		top: 0.5rem !important;
	}
	.fr-range--step[data-fr-js-range] {
		flex-grow: 1;
	}
	.fr-range__custom-label {
		max-width: 8rem;
		margin: 0.5rem 1rem;
	}

	input:disabled {
		-webkit-text-fill-color: var(--body-text-color);
		-webkit-opacity: 1;
		opacity: 1;
	}

	input[disabled] {
		cursor: not-allowed;
	}
</style>
