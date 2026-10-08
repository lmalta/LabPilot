import type { Message } from "./types.js";

export class HistoriqueMessages {
  private readonly messages: Message[];

  public constructor(messages: Message[] = []) {
    this.messages = [...messages];
  }

  public ajouter(message: Message): void {
    this.messages.push(message);
  }

  public obtenir(): Message[] {
    return [...this.messages];
  }
}
