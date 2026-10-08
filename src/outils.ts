import { definitionsOutils } from "./labpilot.js";
import type { ToolExecution, ToolResult } from "./types.js";

export function executerOutil(
  execution: ToolExecution,
): ToolResult {
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

  return {
    success: true,
    result: {
      outil: outil.function.name,
      arguments: execution.arguments,
    },
  };
}