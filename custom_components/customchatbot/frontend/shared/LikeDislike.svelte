<script lang="ts">
	import IconButton from "./IconButton.svelte";
	import ThumbDownActive from "./ThumbDownActive.svelte";
	import ThumbDownDefault from "./ThumbDownDefault.svelte";
	import ThumbUpActive from "./ThumbUpActive.svelte";
	import ThumbUpDefault from "./ThumbUpDefault.svelte";

	export let handle_action: (selected: string | null) => void;

	let selected: "like" | "dislike" | null = null;
</script>

<IconButton
border={true}
	Icon={selected === "dislike" ? ThumbDownActive : ThumbDownDefault}
	label={selected === "dislike" ? "clicked dislike" : "dislike"}
	highlight={selected === "dislike"}
	on:click={() => {
		selected = "dislike";
		handle_action(selected);
	}}
/>

<IconButton
border={true}
	Icon={selected === "like" ? ThumbUpActive : ThumbUpDefault}
	label={selected === "like" ? "clicked like" : "like"}
	highlight={selected === "like"}
	color={selected === "like"
		? "var(--color-accent)"
		: "var(--block-label-text-color)"}
	on:click={() => {
		selected = "like";
		handle_action(selected);
	}}
/>

<style>
	</style>