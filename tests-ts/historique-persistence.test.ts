import test from "node:test";
import assert from "node:assert/strict";

import {
  HistoriqueMessages,
} from "../src/historique.js";
import type {
  Conversation,
  DepotConversations,
} from "../src/depot-conversations.js";
import type { Message } from "../src/types.js";

class DepotConversationsTest
  implements DepotConversations
{
  private readonly messages =
    new Map<string, Message[]>();

  public creerConversation(): Conversation {
    const conversation: Conversation = {
      id: "conversation-test",
      creeLe: "2026-01-01T00:00:00.000Z",
    };

    this.messages.set(
      conversation.id,
      [],
    );

    return conversation;
  }

  public ajouterMessage(
    conversationId: string,
    message: Message,
  ): void {
    const messages =
      this.messages.get(conversationId);

    if (messages === undefined) {
      throw new Error(
        "Conversation inconnue.",
      );
    }

    messages.push(message);
  }

  public obtenirConversation(
    conversationId: string,
  ): Conversation | null {
    if (!this.messages.has(conversationId)) {
      return null;
    }

    return {
      id: conversationId,
      creeLe: "2026-01-01T00:00:00.000Z",
    };
  }

  public obtenirMessages(
    conversationId: string,
  ): Message[] {
    return [
      ...(this.messages.get(conversationId) ?? []),
    ];
  }

  public listerConversations(): Conversation[] {
    return [];
  }
}

test("un historique peut être sauvegardé puis rechargé", () => {
  const depot =
    new DepotConversationsTest();

  const conversation =
    depot.creerConversation();

  const historique =
    new HistoriqueMessages();

  historique.ajouter({
    role: "user",
    content: "Bonjour",
  });

  historique.ajouter({
    role: "assistant",
    content: "Bonjour !",
  });

  historique.sauvegarder(
    depot,
    conversation.id,
  );

  const recharge =
    HistoriqueMessages.charger(
      depot,
      conversation.id,
    );

  assert.deepEqual(
    recharge.obtenir(),
    historique.obtenir(),
  );
});

test("une sauvegarde successive ne duplique pas les messages", () => {
  const depot =
    new DepotConversationsTest();

  const conversation =
    depot.creerConversation();

  const historique =
    new HistoriqueMessages();

  historique.ajouter({
    role: "user",
    content: "Premier message",
  });

  historique.sauvegarder(
    depot,
    conversation.id,
  );

  historique.ajouter({
    role: "assistant",
    content: "Deuxième message",
  });

  historique.sauvegarder(
    depot,
    conversation.id,
  );

  const messages =
    HistoriqueMessages.charger(
      depot,
      conversation.id,
    );

  assert.deepEqual(
    messages.obtenir(),
    [
      {
        role: "user",
        content: "Premier message",
      },
      {
        role: "assistant",
        content: "Deuxième message",
      },
    ],
  );
});

test("un historique chargé ne duplique pas les messages déjà persistés", () => {
  const depot =
    new DepotConversationsTest();

  const conversation =
    depot.creerConversation();

  const historique =
    new HistoriqueMessages();

  historique.ajouter({
    role: "user",
    content: "Message déjà enregistré",
  });

  historique.sauvegarder(
    depot,
    conversation.id,
  );

  const historiqueRecharge =
    HistoriqueMessages.charger(
      depot,
      conversation.id,
    );

  historiqueRecharge.ajouter({
    role: "assistant",
    content: "Nouveau message",
  });

  historiqueRecharge.sauvegarder(
    depot,
    conversation.id,
  );

  const messages =
    HistoriqueMessages.charger(
      depot,
      conversation.id,
    );

  assert.deepEqual(
    messages.obtenir(),
    [
      {
        role: "user",
        content: "Message déjà enregistré",
      },
      {
        role: "assistant",
        content: "Nouveau message",
      },
    ],
  );
});
