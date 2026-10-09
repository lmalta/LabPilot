import test from "node:test";
import assert from "node:assert/strict";

import {
  ServiceConversations,
} from "../src/service-conversations.js";
import type {
  Conversation,
  DepotConversations,
} from "../src/depot-conversations.js";
import {
  HistoriqueMessages,
} from "../src/historique.js";
import {
  Orchestrateur,
} from "../src/orchestrateur.js";
import type {
  Message,
  MessageAssistant,
} from "../src/types.js";

class DepotTest implements DepotConversations {
  private readonly conversations =
    new Map<string, Conversation>();

  private readonly messages =
    new Map<string, Message[]>();

  private prochainId = 1;

  public creerConversation(): Conversation {
    const conversation: Conversation = {
      id: `conversation-${this.prochainId++}`,
      creeLe: "2026-01-01T00:00:00.000Z",
    };

    this.conversations.set(conversation.id, conversation);
    this.messages.set(conversation.id, []);

    return conversation;
  }

  public ajouterMessage(
    conversationId: string,
    message: Message,
  ): void {
    const messages = this.messages.get(conversationId);

    if (messages === undefined) {
      throw new Error("Conversation inconnue.");
    }

    messages.push(message);
  }

  public obtenirConversation(
    conversationId: string,
  ): Conversation | null {
    return this.conversations.get(conversationId) ?? null;
  }

  public obtenirMessages(
    conversationId: string,
  ): Message[] {
    return [...(this.messages.get(conversationId) ?? [])];
  }

  public listerConversations(): Conversation[] {
    return [...this.conversations.values()];
  }
}

type TraitementSimule = (
  historique: HistoriqueMessages,
) => Promise<MessageAssistant>;

function creerService(
  depot: DepotTest,
  traitement: TraitementSimule,
): ServiceConversations {
  const orchestrateur = {
    traiter: async (
      _messages: Message[],
      historique?: HistoriqueMessages,
    ): Promise<MessageAssistant> => {
      if (historique === undefined) {
        throw new Error("Historique attendu.");
      }

      return traitement(historique);
    },
  } as Orchestrateur;

  return new ServiceConversations(depot, orchestrateur);
}

test("le service crée une conversation persistante", () => {
  const depot = new DepotTest();
  const service = creerService(depot, async () => ({
    role: "assistant",
    content: "Réponse",
  }));

  const conversation = service.creerConversation();

  assert.ok(conversation.id);
  assert.deepEqual(
    depot.obtenirConversation(conversation.id),
    conversation,
  );
});

test("un échange sauvegarde le message utilisateur et la réponse finale", async () => {
  const depot = new DepotTest();
  const service = creerService(depot, async (historique) => {
    assert.deepEqual(historique.obtenir(), [
      { role: "user", content: "Bonjour" },
    ]);

    return {
      role: "assistant",
      content: "Bonjour !",
    };
  });

  const conversation = service.creerConversation();

  const reponse = await service.envoyerMessage(
    conversation.id,
    "Bonjour",
  );

  assert.deepEqual(reponse, {
    role: "assistant",
    content: "Bonjour !",
  });

  assert.deepEqual(depot.obtenirMessages(conversation.id), [
    { role: "user", content: "Bonjour" },
    { role: "assistant", content: "Bonjour !" },
  ]);
});

test("les échanges suivants conservent le contexte précédent", async () => {
  const depot = new DepotTest();
  let nombreAppels = 0;

  const service = creerService(depot, async (historique) => {
    nombreAppels += 1;

    if (nombreAppels === 1) {
      return {
        role: "assistant",
        content: "Je m'appelle LabPilot.",
      };
    }

    assert.deepEqual(historique.obtenir(), [
      { role: "user", content: "Qui es-tu ?" },
      { role: "assistant", content: "Je m'appelle LabPilot." },
      { role: "user", content: "Comment t'appelles-tu ?" },
    ]);

    return {
      role: "assistant",
      content: "LabPilot.",
    };
  });

  const conversation = service.creerConversation();

  await service.envoyerMessage(conversation.id, "Qui es-tu ?");
  await service.envoyerMessage(
    conversation.id,
    "Comment t'appelles-tu ?",
  );

  assert.equal(nombreAppels, 2);
  assert.equal(depot.obtenirMessages(conversation.id).length, 4);
});

test("une erreur d'orchestration ne fait pas perdre les messages intermédiaires", async () => {
  const depot = new DepotTest();

  const service = creerService(depot, async (historique) => {
    historique.ajouter({
      role: "assistant",
      content: "",
      tool_calls: [{
        function: {
          name: "etat_systeme",
          arguments: {},
        },
      }],
    });

    historique.ajouter({
      role: "tool",
      tool_name: "etat_systeme",
      content: '{"cpu":12}',
    });

    throw new Error("Erreur simulée");
  });

  const conversation = service.creerConversation();

  await assert.rejects(
    service.envoyerMessage(conversation.id, "État du système"),
    /Erreur simulée/,
  );

  assert.deepEqual(depot.obtenirMessages(conversation.id), [
    { role: "user", content: "État du système" },
    {
      role: "assistant",
      content: "",
      tool_calls: [{
        function: {
          name: "etat_systeme",
          arguments: {},
        },
      }],
    },
    {
      role: "tool",
      tool_name: "etat_systeme",
      content: '{"cpu":12}',
    },
  ]);
});

test("la reprise refuse un identifiant inconnu", () => {
  const service = creerService(
    new DepotTest(),
    async () => ({ role: "assistant", content: "OK" }),
  );

  assert.throws(
    () => service.reprendreConversation("inconnue"),
    /inconnue|introuvable/i,
  );
});
