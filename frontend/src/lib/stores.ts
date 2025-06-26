import { writable } from 'svelte/store';

export const textValue = writable('');
export const currentScreen = writable<'FirstScreen' | 'Chatbots'>('FirstScreen');
export const isLoading = writable(false);
export const hasError = writable(false);
export const mode = writable('random');
export const customModelsDropdown = writable([]);

interface ChatMessage {
  role: string;
  content: string;
  timestamp?: number;
}

interface ConversationState {
  chatbot1: ChatMessage[];
  chatbot2: ChatMessage[];
}

export const conversation = writable<ConversationState>({
  chatbot1: [],
  chatbot2: []
});
