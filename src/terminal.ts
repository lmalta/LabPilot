import { createInterface } from "node:readline/promises";
import { stdin, stdout } from "node:process";
import type { ServiceConversations } from "./service-conversations.js";

export async function lancerTerminal(
  service: ServiceConversations,
): Promise<void> {
  const terminal = createInterface({
    input: stdin,
    output: stdout,
  });

  let conversation = service.creerConversation();

  console.log("\nLabPilot — Assistant local");
  console.log(`Conversation : ${conversation.id}`);
  console.log("Saisis un message, /new, /resume <id>, /help ou /quit.\n");

  try {
    while (true) {
      let saisie: string;

      try {
        saisie = (
          await terminal.question("Vous > ")
        ).trim();
      } catch {
        // Une interruption du terminal met fin à la session.
        break;
      }

      if (saisie === "") {
        continue;
      }

      if (saisie === "/quit") {
        break;
      }

      if (saisie === "/help") {
        console.log(
          "\nCommandes :\n" +
          "  /new           Nouvelle conversation\n" +
          "  /resume <id>   Reprendre une conversation\n" +
          "  /help          Afficher cette aide\n" +
          "  /quit          Quitter LabPilot\n",
        );
        continue;
      }

      if (saisie === "/new") {
        conversation = service.creerConversation();
        console.log(`Nouvelle conversation : ${conversation.id}`);
        continue;
      }

      if (saisie.startsWith("/resume ")) {
        const id = saisie.slice("/resume ".length).trim();

        if (id === "") {
          console.log("Usage : /resume <id>");
          continue;
        }

        try {
          conversation = service.reprendreConversation(id);
          console.log(`Conversation reprise : ${conversation.id}`);
        } catch (erreur) {
          console.error(
            erreur instanceof Error ? erreur.message : erreur,
          );
        }

        continue;
      }

      if (saisie.startsWith("/")) {
        console.log("Commande inconnue. Saisis /help pour l'aide.");
        continue;
      }

      try {
        const reponse = await service.envoyerMessage(
          conversation.id,
          saisie,
        );

        console.log(`\nLabPilot > ${reponse.content}\n`);
      } catch (erreur) {
        console.error(
          "\nErreur :",
          erreur instanceof Error ? erreur.message : erreur,
          "\n",
        );
      }
    }
  } finally {
    terminal.close();
    console.log("\nFin de la session LabPilot.");
  }
}
