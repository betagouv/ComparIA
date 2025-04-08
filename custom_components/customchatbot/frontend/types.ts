import type { FileData } from "@gradio/client";

export type MessageRole = "system" | "user" | "assistant";

export interface Metadata {
	bot: string | null;
	generation_id: string | null;
	duration: number | null;
}

export interface Message {
	role: MessageRole;
	metadata: Metadata;
	content: string;
	reasoning?: string;
	index: number | [number, number];
	liked?: boolean;
	disliked?: boolean;
	prefs?: string[];
	comment: string;
	commented?: boolean;
	error?: string;
}

export interface TextMessage extends Message {
	content: string;
	reasoning?: string;
	liked?: boolean;
	disliked?: boolean;
	prefs?: string[];
	comment: string;
	commented?: boolean;
	error?: string;
}

export interface ExampleMessage {
	icon?: FileData;
	display_text?: string;
	text: string;
	files?: FileData[];
}

export type message_data = string | null;


export type NormalisedMessage = TextMessage;
