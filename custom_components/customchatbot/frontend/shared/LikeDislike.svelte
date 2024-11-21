<script lang="ts">
	import IconButton from "./IconButton.svelte";
	import ThumbDownActive from "./ThumbDownActive.svelte";
	import ThumbDownDefault from "./ThumbDownDefault.svelte";
	import ThumbDownDisabled from "./ThumbDownDisabled.svelte";
	import ThumbUpActive from "./ThumbUpActive.svelte";
	import ThumbUpDefault from "./ThumbUpDefault.svelte";
	import ThumbUpDisabled from "./ThumbUpDisabled.svelte";

	export let handle_action: (selected: string | null) => void;
	export let disabled = false;

	let selected: "like" | "dislike" | null = null;
</script>

<IconButton
	{disabled}
	border={true}
	Icon={disabled
		? ThumbUpDisabled
		: selected === "like"
			? ThumbUpActive
			: ThumbUpDefault}
	label={selected === "like" ? "j'apprécie (sélectionné)" : "j'apprécie"}
	highlight={selected === "like"}
	on:click={() => {
		if (selected === "like") {
			selected = null; // Unselect the "like"
			handle_action("none"); // Notify that no action is selected
		} else {
			selected = "like"; // Select the "like"
			handle_action("like"); // Notify that "like" was selected
		}
	}}
/>

<IconButton
	{disabled}
	border={true}
	Icon={disabled
		? ThumbDownDisabled
		: selected === "dislike"
			? ThumbDownActive
			: ThumbDownDefault}
	label={selected === "dislike"
		? "je n'apprécie pas (sélectionné)"
		: "je n'apprécie pas"}
	highlight={selected === "dislike"}
	on:click={() => {
		if (selected === "dislike") {
			selected = null; // Unselect the "dislike"
			handle_action("none"); // Notify that no action is selected
		} else {
			selected = "dislike"; // Select the "dislike"
			handle_action("dislike"); // Notify that "dislike" was selected
		}
	}}
/>

