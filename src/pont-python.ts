import { spawn } from "node:child_process";

import type { ToolExecution, ToolResult } from "./types.js";

export function executerAvecPython(
  execution: ToolExecution,
): Promise<ToolResult> {
  return new Promise((resolve, reject) => {
    const processus = spawn(
      ".venv/bin/python",
      ["-m", "labpilot.bridge"],
    );

    let sortie = "";
    let erreur = "";

    processus.stdout.on("data", (donnees: Buffer) => {
      sortie += donnees.toString();
    });

    processus.stderr.on("data", (donnees: Buffer) => {
      erreur += donnees.toString();
    });

    processus.on("error", (erreurProcessus) => {
      reject(erreurProcessus);
    });

    processus.on("close", (code) => {
      if (code !== 0) {
        reject(
          new Error(
            `Le processus Python s est terminé avec le code ${code}: ${erreur}`,
          ),
        );
        return;
      }

      try {
        const resultat = JSON.parse(sortie) as ToolResult;
        resolve(resultat);
      } catch {
        reject(
          new Error(
            `La réponse Python n est pas un JSON valide: ${sortie}`,
          ),
        );
      }
    });

    processus.stdin.write(
      `${JSON.stringify(execution)}\n`,
    );

    processus.stdin.end();
  });
}