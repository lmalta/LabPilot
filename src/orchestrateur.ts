import {
  convertirResultatEnMessageOutil,
  convertirToolCallEnExecution,
  OllamaClient,
} from "./ollama.js";
import { executerOutil } from "./outils.js";
import { PontPython } from "./pont-python.js";
import type {
  Message,
  MessageAssistant,
  ToolResult,
} from "./types.js";
import { HistoriqueMessages } from "./historique.js";

export class Orchestrateur {
  public constructor(
    private readonly pont: PontPython,
    private readonly ollama: OllamaClient,
    private readonly maxIterations = 10,
  ) {}

  public async executerAppelOutil(
    message: Extract<Message, { role: "assistant" }>,
  ): Promise<ToolResult> {
    if (message.tool_calls === undefined) {
      throw new Error(
        "Le message assistant ne contient aucun appel d outil.",
      );
    }

    const appel = message.tool_calls[0];

    if (appel === undefined) {
      throw new Error(
        "Le message assistant contient une liste d appels d outils vide.",
      );
    }

    const execution =
      convertirToolCallEnExecution(appel);

    return executerOutil(this.pont, execution);
  }

  public async traiter(
  messages: Message[],
): Promise<MessageAssistant> {
  const historique = new HistoriqueMessages(messages);

  for (
    let iteration = 0;
    iteration < this.maxIterations;
    iteration += 1
  ) {
    const reponse = await this.ollama.chat(
      historique.obtenir(),
    );

    if (
      reponse.tool_calls === undefined ||
      reponse.tool_calls.length === 0
    ) {
      return reponse;
    }

    const appel = reponse.tool_calls[0];

    if (appel === undefined) {
      throw new Error(
        "Ollama a retourné une liste d appels d outils vide.",
      );
    }

    const execution =
      convertirToolCallEnExecution(appel);

    const resultat = await executerOutil(
      this.pont,
      execution,
    );

    const messageOutil =
      convertirResultatEnMessageOutil(
        execution.name,
        resultat,
      );

    historique.ajouter(reponse);
    historique.ajouter(messageOutil);
  }

  throw new Error(
    `La limite de ${this.maxIterations} itérations d orchestration a été atteinte.`,
  );
}
}
