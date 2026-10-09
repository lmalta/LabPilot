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
  {
    type: "function",
    function: {
      name: "etat_home_assistant",
      description:
        "Retourne la version de Home Assistant, le nombre d'entités et leur répartition par domaine. Cet outil est en lecture seule.",
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
      name: "etat_proxmox",
      description:
        "Consulte en lecture seule le cluster Proxmox. " +
        "Les champs type, id, nom, noeud et etat proviennent " +
        "des données de l'API. Le type vaut VM ou conteneur " +
        "et ne doit jamais être déduit de l'état. Les états " +
        "possibles comprennent running, stopped et unknown. " +
        "Un état unknown n'est pas un état stopped. " +
        "Si le nom vaut null, il est inconnu et ne doit pas " +
        "être inventé. Pour les totaux, utilise les compteurs " +
        "fournis par l'outil. Les compteurs machines_par_type et " +
        "machines_par_etat donnent les totaux de référence. " +
        "Pour une répartition croisée par type et état, utilise " +
        "directement machines_par_type_et_etat. Ce compteur " +
        "contient les états running, stopped et unknown, avec " +
        "des valeurs à zéro si nécessaire. Ne reconstruis pas " +
        "cette répartition à partir de la liste détaillée. " +
        "Si tu fournis un détail par état ou par nœud, vérifie " +
        "que les nombres correspondent exactement aux données. " +
        "Ne présente pas de répartition que tu ne peux pas " +
        "vérifier. Le total des états doit être égal au nombre " +
        "total de machines.",
      parameters: {
        type: "object",
        properties: {},
        required: [],
      },
    },
  },
];
