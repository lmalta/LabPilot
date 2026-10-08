import {
  creerMessageUtilisateur,
  definitionsOutils,
  obtenirInformations,
} from "./labpilot.js";

const informations = obtenirInformations();
const message = creerMessageUtilisateur("Quel est l'état du système ?");

console.log(definitionsOutils);
console.log(informations);
console.log(message);
