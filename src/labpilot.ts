import type { MessageUser, ToolDefinition } from "./types.js";

export interface InformationsLabPilot {
  nom: string;
  version: string;
  langage: string;
}

export function obtenirInformations(): InformationsLabPilot {
  return {
    nom: "LabPilot",
    version: "0.1.0",
    langage: "TypeScript",
  };
}

export function creerMessageUtilisateur(
  contenu: string,
): MessageUser {
  return {
    role: "user",
    content: contenu,
  };
}

export const definitionsOutils: ToolDefinition[] = [
  {
    type: "function",
    function: {
      name: "heure_actuelle",
      description: "Retourne l heure actuelle.",
      parameters: {
        type: "object",
        properties: {},
        required: [],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "heure_dans",
      description: "Retourne l heure dans un nombre de minutes donné.",
      parameters: {
        type: "object",
        properties: {
          minutes: {
            type: "integer",
            description: "Nombre de minutes à ajouter à l heure actuelle.",
          },
        },
        required: ["minutes"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "etat_systeme",
      description: "Retourne l état actuel du système.",
      parameters: {
        type: "object",
        properties: {},
        required: [],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "etat_gpu",
      description: "Retourne l état des GPU NVIDIA visibles par le système.",
      parameters: {
        type: "object",
        properties: {},
        required: [],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "etat_ollama",
      description:
        "Retourne l état du serveur Ollama, les modèles disponibles et les modèles actuellement actifs.",
      parameters: {
        type: "object",
        properties: {},
        required: [],
      },
    },
  },
];
