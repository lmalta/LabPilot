import type {
  Conversation,
  DepotConversations,
} from "./depot-conversations.js";
import { HistoriqueMessages } from "./historique.js";
import { Orchestrateur } from "./orchestrateur.js";
import type { MessageAssistant } from "./types.js";

export class ServiceConversations {
  public constructor(
    private readonly depot: DepotConversations,
    private readonly orchestrateur: Orchestrateur,
  ) {}

  public creerConversation(): Conversation {
    return this.depot.creerConversation();
  }

  public reprendreConversation(
    conversationId: string,
  ): Conversation {
    const conversation =
      this.depot.obtenirConversation(conversationId);

    if (conversation === null) {
      throw new Error(
        `Conversation introuvable : ${conversationId}`,
      );
    }

    return conversation;
  }

  public async envoyerMessage(
    conversationId: string,
    contenu: string,
  ): Promise<MessageAssistant> {
    this.reprendreConversation(conversationId);

    const historique = HistoriqueMessages.charger(
      this.depot,
      conversationId,
    );

    historique.ajouter({
      role: "user",
      content: contenu,
    });

    // Sauvegarde immédiate du message utilisateur.
    historique.sauvegarder(
      this.depot,
      conversationId,
    );

    try {
      const reponse = await this.orchestrateur.traiter(
        [],
        historique,
      );

      // L'orchestrateur ne stocke pas lui-même la réponse finale.
      historique.ajouter(reponse);

      return reponse;
    } finally {
      // Sauvegarde également les appels d'outils et leurs résultats
      // si l'orchestration échoue.
      historique.sauvegarder(
        this.depot,
        conversationId,
      );
    }
  }
}
