import Database from "better-sqlite3";
import { randomUUID } from "node:crypto";

import type {
  Conversation,
  DepotConversations,
} from "./depot-conversations.js";
import type { Message } from "./types.js";

export class DepotConversationsSQLite
  implements DepotConversations
{
  private readonly base: Database.Database;

  public constructor(
    chemin: string = "data/labpilot.db",
  ) {
    this.base = new Database(chemin);
    this.initialiserSchema();
  }

  private initialiserSchema(): void {
    this.base.exec(`
      CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        cree_le TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        ordre INTEGER NOT NULL,
        role TEXT NOT NULL,
        contenu TEXT NOT NULL,
        nom_outil TEXT,
        FOREIGN KEY (conversation_id)
          REFERENCES conversations(id)
          ON DELETE CASCADE
      );

      CREATE INDEX IF NOT EXISTS
        idx_messages_conversation_ordre
      ON messages(conversation_id, ordre);
    `);
  }

  public creerConversation(): Conversation {
    const conversation: Conversation = {
      id: randomUUID(),
      creeLe: new Date().toISOString(),
    };

    const requete = this.base.prepare(`
      INSERT INTO conversations (
        id,
        cree_le
      )
      VALUES (
        @id,
        @creeLe
      )
    `);

    requete.run({
      id: conversation.id,
      creeLe: conversation.creeLe,
    });

    return conversation;
  }

  public ajouterMessage(
    conversationId: string,
    message: Message,
  ): void {
    const requete = this.base.prepare(`
      INSERT INTO messages (
        conversation_id,
        ordre,
        role,
        contenu,
        nom_outil
      )
      SELECT
        @conversationId,
        COALESCE(MAX(ordre), -1) + 1,
        @role,
        @contenu,
        @nomOutil
      FROM messages
      WHERE conversation_id = @conversationId
    `);

    requete.run({
      conversationId,
      role: message.role,
      contenu: message.content,
      nomOutil:
        message.role === "tool"
          ? message.tool_name
          : null,
    });
  }

  public obtenirConversation(
    conversationId: string,
  ): Conversation | null {
    const requete = this.base.prepare(`
      SELECT
        id,
        cree_le AS creeLe
      FROM conversations
      WHERE id = ?
    `);

    const resultat = requete.get(
      conversationId,
    ) as Conversation | undefined;

    return resultat ?? null;
  }

  public obtenirMessages(
    conversationId: string,
  ): Message[] {
    const requete = this.base.prepare(`
      SELECT
        role,
        contenu,
        nom_outil
      FROM messages
      WHERE conversation_id = ?
      ORDER BY ordre ASC
    `);

    const lignes = requete.all(
      conversationId,
    ) as Array<{
      role: Message["role"];
      contenu: string;
      nom_outil: string | null;
    }>;

    return lignes.map((ligne) => {
      if (ligne.role === "tool") {
        return {
          role: "tool",
          content: ligne.contenu,
          tool_name: ligne.nom_outil ?? "",
        };
      }

      if (ligne.role === "assistant") {
        return {
          role: "assistant",
          content: ligne.contenu,
        };
      }

      if (ligne.role === "system") {
        return {
          role: "system",
          content: ligne.contenu,
        };
      }

      return {
        role: "user",
        content: ligne.contenu,
      };
    });
  }

  public listerConversations(): Conversation[] {
    const requete = this.base.prepare(`
      SELECT
        id,
        cree_le AS creeLe
      FROM conversations
      ORDER BY cree_le ASC
    `);

    return requete.all() as Conversation[];
  }

  public fermer(): void {
    this.base.close();
  }
}
