import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { createInterface, type Interface } from "node:readline";

import type { ToolExecution, ToolResult } from "./types.js";

export class PontPython {
  private processus: ChildProcessWithoutNullStreams | null = null;
  private lecture: Interface | null = null;
  private attente: Promise<ToolResult> | null = null;
  private resoudreAttente: ((resultat: ToolResult) => void) | null = null;
  private rejeterAttente: ((erreur: Error) => void) | null = null;

  public démarrer(): void {
    if (this.processus !== null) {
      return;
    }

    const processus = spawn(
      ".venv/bin/python",
      ["-m", "labpilot.bridge"],
    );

    this.processus = processus;

    this.lecture = createInterface({
      input: processus.stdout,
    });

    this.lecture.on("line", (ligne) => {
      if (
        this.resoudreAttente === null ||
        this.rejeterAttente === null
      ) {
        return;
      }

      try {
        const resultat = JSON.parse(ligne) as ToolResult;

        this.resoudreAttente(resultat);
      } catch {
        this.rejeterAttente(
          new Error(
            `La réponse Python n est pas un JSON valide: ${ligne}`,
          ),
        );
      }

      this.attente = null;
      this.resoudreAttente = null;
      this.rejeterAttente = null;
    });

    processus.on("error", (erreur) => {
      if (this.rejeterAttente !== null) {
        this.rejeterAttente(erreur);
      }
    });

    processus.on("close", (code) => {
      if (this.processus !== processus) {
        return;
      }

      this.processus = null;
      this.lecture?.close();
      this.lecture = null;

      if (this.rejeterAttente !== null) {
        this.rejeterAttente(
          new Error(
            `Le processus Python s est terminé avec le code ${code}.`,
          ),
        );
      }

      this.attente = null;
      this.resoudreAttente = null;
      this.rejeterAttente = null;
    });
  }

  public executer(
    execution: ToolExecution,
  ): Promise<ToolResult> {
    if (this.processus === null) {
      return Promise.reject(
        new Error("Le pont Python n est pas démarré."),
      );
    }

    if (this.attente !== null) {
      return Promise.reject(
        new Error(
          "Une exécution Python est déjà en attente.",
        ),
      );
    }

    this.attente = new Promise<ToolResult>(
      (resoudre, rejeter) => {
        this.resoudreAttente = resoudre;
        this.rejeterAttente = rejeter;
      },
    );

    this.processus.stdin.write(
      `${JSON.stringify(execution)}\n`,
    );

    return this.attente;
  }

  public arrêter(): void {
    const processus = this.processus;

    if (processus === null) {
      return;
    }

    this.lecture?.close();
    this.lecture = null;

    if (this.rejeterAttente !== null) {
      this.rejeterAttente(
        new Error(
          "Le processus Python a été arrêté pendant une exécution.",
        ),
      );
    }

    this.attente = null;
    this.resoudreAttente = null;
    this.rejeterAttente = null;

    this.processus = null;

    processus.stdin.end();
  }
}