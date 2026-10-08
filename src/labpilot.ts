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
