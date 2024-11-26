import type { FileData } from "@gradio/client";

export type MessageRole = "system" | "user" | "assistant";

export interface Metadata {
	title: string | null;
	bot: string | null;
}

export interface ComponentData {
	component: string;
	constructor_args: any;
	props: any;
	value: any;
	alt_text: string | null;
}

export interface Message {
	role: MessageRole;
	type: string;
	metadata: Metadata;
	content: string | FileData | ComponentData;
	index: number | [number, number];
	liked?: boolean;
	disliked?: boolean;
	prefs?: string[];
	comment: string
}

export interface TextMessage extends Message {
	type: "text";
	content: string;
	liked: boolean;
	disliked: boolean;
	prefs?: string[];
	comment: string	
}

export interface ComponentMessage extends Message {
	type: "component";
	content: ComponentData;
	liked: boolean;
	disliked: boolean;
	prefs?: string[];
	comment: string
}

export interface ExampleMessage {
	icon?: FileData;
	display_text?: string;
	text: string;
	files?: FileData[];
}

export type message_data =
	| string
	| { file: FileData | FileData[]; alt_text: string | null }
	| { component: string; value: any; constructor_args: any; props: any }
	| null;

export type TupleFormat = [message_data, message_data][] | null;

export type NormalisedMessage = TextMessage | ComponentMessage;
