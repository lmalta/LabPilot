import type { Message } from "./types.js";

export interface Conversation {
  id: string;
  creeLe: string;
}

export interface DepotConversations {
  creerConversation(): Conversation;

  ajouterMessage(
    conversationId: string,
    message: Message,
  ): void;

  obtenirConversation(
    conversationId: string,
  ): Conversation | null;

  obtenirMessages(
    conversationId: string,
  ): Message[];

  listerConversations(): Conversation[];
}
