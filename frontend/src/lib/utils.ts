import type { FileData } from '@gradio/client';

import type { NormalisedMessage, Message, MessageRole } from '../types';

export interface UndoRetryData {
  index: number | [number, number];
  value: string | FileData;
}

const redirect_src_url = (src: string, root: string): string =>
  src.replace('src="/file', `src="${root}file`);

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
        index: i,
        comment: message.comment !== undefined ? message.comment : '',
        liked: message.liked !== undefined ? message.liked : false,
        disliked: message.disliked !== undefined ? message.disliked : false,
        commented: message.commented !== undefined ? message.commented : false,
        error: message.error !== undefined ? message.error : null,
        reasoning: message.reasoning !== undefined ? message.reasoning : ''
      };
    });
  }

  return new_messages.map((message, i) => {
    const oldMessage = old_messages[i];

    return {
      ...oldMessage, // spread the old message first
      ...message, // override with the new message

      role: message.role,
      metadata: message.metadata,
      content: redirect_src_url(message.content, root),
      index: i,
      error: message.error !== undefined ? message.error : oldMessage?.error || false,
      liked: message.liked !== undefined ? message.liked : oldMessage?.liked || false,
      disliked: message.disliked !== undefined ? message.disliked : oldMessage?.disliked || false,
      commented:
        message.commented !== undefined ? message.commented : oldMessage?.commented || false,
      // prefs: message.prefs !== undefined ? message.prefs : oldMessage?.prefs || [],
      reasoning: message.reasoning !== undefined ? message.reasoning : ''
    };
  });
}

export function is_one_of_last_two_bot_msgs(
  messages: NormalisedMessage[],
  all_messages: NormalisedMessage[]
): boolean {
  const lastMsgs = messages
    .slice(-2)
    .map((msg) => ({
      ...msg,
      isLast:
        JSON.stringify(msg.index) === JSON.stringify(all_messages[all_messages.length - 1].index) ||
        JSON.stringify(msg.index) === JSON.stringify(all_messages[all_messages.length - 2].index)
    }));
  return lastMsgs.some((msg) => msg.role === 'assistant' && msg.isLast);
}

export function group_messages(messages: NormalisedMessage[]): NormalisedMessage[][] {
  const groupedMessages: NormalisedMessage[][] = [];
  let currentGroup: NormalisedMessage[] = [];
  let currentRole: MessageRole | null = null;

  for (const message of messages) {
    if (!(message.role === 'assistant' || message.role === 'user')) {
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
