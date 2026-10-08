
import { definitionsOutils } from "./labpilot.js";
import { PontPython } from "./pont-python.js";
import type { ToolExecution, ToolResult } from "./types.js";

export async function executerOutil(
  pont: PontPython,
  execution: ToolExecution,
): Promise<ToolResult> {
  const outil = definitionsOutils.find(
    (definition) => definition.function.name === execution.name,
  );

  if (!outil) {
    return {
      success: false,
      error: {
        type: "OutilInconnu",
        message: `L outil "${execution.name}" n existe pas.`,
      },
    };
  }

  return pont.executer(execution);
}