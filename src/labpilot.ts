import type { MessageUser } from "./types.js";

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