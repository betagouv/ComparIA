import type { FileData } from "@gradio/client";
import type { ComponentType, SvelteComponent } from "svelte";
import { uploadToHuggingFace } from "@gradio/utils";
import type {
	TupleFormat,
	ComponentMessage,
	ComponentData,
	TextMessage,
	NormalisedMessage,
	Message,
	MessageRole
} from "../types";
import type { LoadedComponent } from "../../core/src/types";
import { Gradio } from "@gradio/utils";
export const format_chat_for_sharing = async (
	chat: [string | FileData | null, string | FileData | null][]
): Promise<string> => {
	let messages = await Promise.all(
		chat.map(async (message_pair) => {
			return await Promise.all(
				message_pair.map(async (message, i) => {
					if (message === null) return "";
					let speaker_emoji = i === 0 ? "😃" : "🤖";
					let html_content = "";

					if (typeof message === "string") {
						const regexPatterns = {
							audio: /<audio.*?src="(\/file=.*?)"/g,
							video: /<video.*?src="(\/file=.*?)"/g,
							image: /<img.*?src="(\/file=.*?)".*?\/>|!\[.*?\]\((\/file=.*?)\)/g
						};

						html_content = message;

						for (let [_, regex] of Object.entries(regexPatterns)) {
							let match;

							while ((match = regex.exec(message)) !== null) {
								const fileUrl = match[1] || match[2];
								const newUrl = await uploadToHuggingFace(fileUrl, "url");
								html_content = html_content.replace(fileUrl, newUrl);
							}
						}
					} else {
						if (!message?.url) return "";
						const file_url = await uploadToHuggingFace(message.url, "url");
						if (message.mime_type?.includes("audio")) {
							html_content = `<audio controls src="${file_url}"></audio>`;
						} else if (message.mime_type?.includes("video")) {
							html_content = file_url;
						} else if (message.mime_type?.includes("image")) {
							html_content = `<img src="${file_url}" />`;
						}
					}

					return `${speaker_emoji}: ${html_content}`;
				})
			);
		})
	);
	return messages
		.map((message_pair) =>
			message_pair.join(
				message_pair[0] !== "" && message_pair[1] !== "" ? "\n" : ""
			)
		)
		.join("\n");
};

export interface UndoRetryData {
	index: number | [number, number];
	value: string | FileData | ComponentData;
}

const redirect_src_url = (src: string, root: string): string =>
	src.replace('src="/file', `src="${root}file`);

function get_component_for_mime_type(
	mime_type: string | null | undefined
): string {
	if (!mime_type) return "file";
	if (mime_type.includes("audio")) return "audio";
	if (mime_type.includes("video")) return "video";
	if (mime_type.includes("image")) return "image";
	return "file";
}

function convert_file_message_to_component_message(
	message: any
): ComponentData {
	const _file = Array.isArray(message.file) ? message.file[0] : message.file;
	return {
		component: get_component_for_mime_type(_file?.mime_type),
		value: message.file,
		alt_text: message.alt_text,
		constructor_args: {},
		props: {}
	} as ComponentData;
}

export function update_messages(
	new_messages: Message[] | null,
	old_messages: Message[] | null,
	root: string
): NormalisedMessage[] | null {
	// console.log("new_messages", new_messages);
	// console.log("old_messages", old_messages);
	if (new_messages === null) return new_messages;
	if (old_messages === null) {
		// If there are no old messages, just return the new messages as is
		return new_messages.map((message, i) => {
		  return {
			role: message.role,
			metadata: message.metadata,
			content: redirect_src_url(message.content, root),
			type: "text",
			index: i,
			comment: message.comment !== undefined ? message.comment : "",
			liked: message.liked !== undefined ? message.liked : false,
			disliked: message.disliked !== undefined ? message.disliked : false,
			commented: message.commented !== undefined ? message.commented : false,
			error: message.error !== undefined ? message.error : false
		  };
		});
	  }
	
	return new_messages.map((message, i) => {
		const oldMessage = old_messages[i];

		if (typeof message.content === "string") {
			return {
				...oldMessage, // spread the old message first
				...message, // override with the new message
		  
				role: message.role,
				metadata: message.metadata,
				content: redirect_src_url(message.content, root),
				type: "text",
				index: i,
				error: message.error !== undefined ? message.error : oldMessage?.error || false,
				liked: message.liked !== undefined ? message.liked : oldMessage?.liked || false,
				disliked: message.disliked !== undefined ? message.disliked : oldMessage?.disliked || false,
				commented: message.commented !== undefined ? message.commented : oldMessage?.commented || false,
				// prefs: message.prefs !== undefined ? message.prefs : oldMessage?.prefs || [],


			};
		}
		return { type: "component", ...message } as ComponentMessage;
	});
}

export function is_component_message(
	message: NormalisedMessage
): message is ComponentMessage {
	return message.type === "component";
}

export function is_one_of_last_two_bot_msgs(
	messages: NormalisedMessage[],
	all_messages: NormalisedMessage[]
): boolean {
	const lastMsgs = messages.slice(-2).map(msg => ({ ...msg, isLast: JSON.stringify(msg.index) === JSON.stringify(all_messages[all_messages.length - 1].index) || JSON.stringify(msg.index) === JSON.stringify(all_messages[all_messages.length - 2].index) }));
	return lastMsgs.some(msg => msg.role === "assistant" && msg.isLast);
}

export function group_messages(
	messages: NormalisedMessage[],
	msg_format: "messages" | "tuples"
): NormalisedMessage[][] {
	const groupedMessages: NormalisedMessage[][] = [];
	let currentGroup: NormalisedMessage[] = [];
	let currentRole: MessageRole | null = null;

	for (const message of messages) {
		if (!(message.role === "assistant" || message.role === "user")) {
			continue;
		}
		if (message.role === currentRole) {
			currentGroup.push(message);
		} else {
			if (currentGroup.length > 0) {
				groupedMessages.push(currentGroup);
			}
			currentGroup = [message];
			currentRole = message.role;
		}
	}

	if (currentGroup.length > 0) {
		groupedMessages.push(currentGroup);
	}

	return groupedMessages;
}

export async function load_components(
	component_names: string[],
	_components: Record<string, ComponentType<SvelteComponent>>,
	load_component: Gradio["load_component"]
): Promise<Record<string, ComponentType<SvelteComponent>>> {
	let names: string[] = [];
	let components: ReturnType<typeof load_component>["component"][] = [];

	component_names.forEach((component_name) => {
		if (_components[component_name] || component_name === "file") {
			return;
		}

		const { name, component } = load_component(component_name, "base");
		names.push(name);
		components.push(component);
		component_name;
	});

	const loaded_components: LoadedComponent[] = await Promise.all(components);
	loaded_components.forEach((component, i) => {
		_components[names[i]] = component.default;
	});

	return _components;
}

export function get_components_from_messages(
	messages: NormalisedMessage[] | null
): string[] {
	if (!messages) return [];
	let components: Set<string> = new Set();
	messages.forEach((message) => {
		if (message.type === "component") {
			components.add(message.content.component);
		}
	});
	return Array.from(components);
}
