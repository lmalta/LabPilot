import { mkdirSync } from "node:fs";
import { OLLAMA_MODEL, OLLAMA_URL } from "./configuration.js";
import { DepotConversationsSQLite } from "./depot-conversations-sqlite.js";
import { OllamaClient } from "./ollama.js";
import { Orchestrateur } from "./orchestrateur.js";
import { PontPython } from "./pont-python.js";
import { ServiceConversations } from "./service-conversations.js";
import { lancerTerminal } from "./terminal.js";

async function main(): Promise<void> {
  if (
    OLLAMA_URL.includes("<") ||
    OLLAMA_MODEL.includes("<") ||
    OLLAMA_URL.trim() === "" ||
    OLLAMA_MODEL.trim() === ""
  ) {
    throw new Error(
      "Configuration Ollama invalide. Vérifie OLLAMA_URL et OLLAMA_MODEL dans .env.",
    );
  }

  let url: URL;

  try {
    url = new URL(OLLAMA_URL);
  } catch {
    throw new Error("OLLAMA_URL doit être une URL valide.");
  }

  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new Error("OLLAMA_URL doit utiliser HTTP ou HTTPS.");
  }

  mkdirSync("data", { recursive: true });

  const depot = new DepotConversationsSQLite();
  const pont = new PontPython();

  try {
    const ollama = new OllamaClient();
    const orchestrateur = new Orchestrateur(pont, ollama);
    const service = new ServiceConversations(depot, orchestrateur);

    pont.démarrer();
    await lancerTerminal(service);
  } finally {
    pont.arrêter();
    depot.fermer();
  }
}

main().catch((erreur: unknown) => {
  console.error(
    "Impossible de démarrer LabPilot :",
    erreur instanceof Error ? erreur.message : erreur,
  );
  process.exitCode = 1;
});
