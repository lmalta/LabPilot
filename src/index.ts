import {
  creerMessageUtilisateur,
  obtenirInformations,
} from "./labpilot.js";

const informations = obtenirInformations();
const message = creerMessageUtilisateur("Quel est l'état du système ?");

console.log(informations);
console.log(message);