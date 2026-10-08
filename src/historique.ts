import type { DepotConversations } from "./depot-conversations.js";
import type { Message } from "./types.js";

export class HistoriqueMessages {
  private readonly messages: Message[];
  private nombreMessagesSauvegardes = 0;

  public constructor(
    messages: Message[] = [],
  ) {
    this.messages = [...messages];
  }

  public ajouter(message: Message): void {
    this.messages.push(message);
  }

  public obtenir(): Message[] {
    return [...this.messages];
  }

  public sauvegarder(
    depot: DepotConversations,
    conversationId: string,
  ): void {
    for (
      let index = this.nombreMessagesSauvegardes;
      index < this.messages.length;
      index += 1
    ) {
      const message = this.messages[index];

      if (message === undefined) {
        continue;
      }

      depot.ajouterMessage(
        conversationId,
        message,
      );
    }

    this.nombreMessagesSauvegardes =
      this.messages.length;
  }

  public static charger(
    depot: DepotConversations,
    conversationId: string,
  ): HistoriqueMessages {
    const messages =
      depot.obtenirMessages(
        conversationId,
      );

    const historique =
      new HistoriqueMessages(
        messages,
      );

    historique.nombreMessagesSauvegardes =
      messages.length;

    return historique;
  }
}
