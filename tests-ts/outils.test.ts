
import assert from "node:assert/strict";
import test from "node:test";

import { definitionsOutils } from "../src/labpilot.js";
import type { ToolExecution, ToolResult } from "../src/types.js";
import { executerOutil } from "../src/outils.js";
import { executerAvecPython } from "../src/pont-python.js";

const outilsAttendus = [
  "heure_actuelle",
  "heure_dans",
  "etat_systeme",
  "etat_gpu",
  "etat_ollama",
];

test("l'outil heure_actuelle est correctement défini", () => {
  const outil = definitionsOutils.find(
    (outil) => outil.function.name === "heure_actuelle",
  );

  assert.ok(outil);
  assert.equal(outil.type, "function");
  assert.equal(outil.function.parameters.type, "object");
});

test("l'outil heure_dans est correctement défini", () => {
  const outil = definitionsOutils.find(
    (outil) => outil.function.name === "heure_dans",
  );

  assert.ok(outil);
  assert.equal(outil.type, "function");
  assert.equal(outil.function.parameters.type, "object");
  assert.ok("minutes" in outil.function.parameters.properties);
  assert.deepEqual(outil.function.parameters.required, ["minutes"]);
});

test("l'outil etat_systeme est correctement défini", () => {
  const outil = definitionsOutils.find(
    (outil) => outil.function.name === "etat_systeme",
  );

  assert.ok(outil);
  assert.equal(outil.type, "function");
  assert.equal(outil.function.parameters.type, "object");
});

test("l'outil etat_gpu est correctement défini", () => {
  const outil = definitionsOutils.find(
    (outil) => outil.function.name === "etat_gpu",
  );

  assert.ok(outil);
  assert.equal(outil.type, "function");
  assert.equal(outil.function.parameters.type, "object");
});

test("l'outil etat_ollama est correctement défini", () => {
  const outil = definitionsOutils.find(
    (outil) => outil.function.name === "etat_ollama",
  );

  assert.ok(outil);
  assert.equal(outil.type, "function");
  assert.equal(outil.function.parameters.type, "object");
});

test("le catalogue contient exactement les cinq outils attendus", () => {
  assert.deepEqual(
    definitionsOutils.map((outil) => outil.function.name),
    outilsAttendus,
  );
});

test("une exécution d'outil peut contenir des arguments", () => {
  const execution: ToolExecution = {
    name: "heure_dans",
    arguments: {
      minutes: 30,
    },
  };

  assert.equal(execution.name, "heure_dans");
  assert.deepEqual(execution.arguments, {
    minutes: 30,
  });
});

test("un résultat d'outil peut représenter un succès", () => {
  const resultat: ToolResult = {
    success: true,
    result: {
      valeur: "résultat de test",
    },
  };

  assert.equal(resultat.success, true);
  assert.deepEqual(resultat.result, {
    valeur: "résultat de test",
  });
});

test("un résultat d'outil peut représenter une erreur", () => {
  const resultat: ToolResult = {
    success: false,
    error: {
      type: "ErreurTest",
      message: "Erreur de test",
    },
  };

  assert.equal(resultat.success, false);
  assert.deepEqual(resultat.error, {
    type: "ErreurTest",
    message: "Erreur de test",
  });
});

test("un outil connu peut être préparé pour exécution", () => {
  const resultat = executerOutil({
    name: "heure_actuelle",
    arguments: {},
  });

  assert.equal(resultat.success, true);
  assert.deepEqual(resultat.result, {
    outil: "heure_actuelle",
    arguments: {},
  });
});

test("un outil connu conserve ses arguments", () => {
  const resultat = executerOutil({
    name: "heure_dans",
    arguments: {
      minutes: 30,
    },
  });

  assert.equal(resultat.success, true);
  assert.deepEqual(resultat.result, {
    outil: "heure_dans",
    arguments: {
      minutes: 30,
    },
  });
});

test("un outil inconnu retourne une erreur", () => {
  const resultat = executerOutil({
    name: "outil_inexistant",
    arguments: {},
  });

  assert.equal(resultat.success, false);
  assert.deepEqual(resultat.error, {
    type: "OutilInconnu",
    message: 'L outil "outil_inexistant" n existe pas.',
  });
});

test("un outil peut être exécuté par Python depuis TypeScript", async () => {
  const resultat = await executerAvecPython({
    name: "heure_actuelle",
    arguments: {},
  });

  assert.equal(resultat.success, true);
  assert.equal(typeof resultat.result, "string");
});

test("un outil Python peut recevoir des arguments depuis TypeScript", async () => {
  const resultat = await executerAvecPython({
    name: "heure_dans",
    arguments: {
      minutes: 30,
    },
  });

  assert.equal(resultat.success, true);
  assert.equal(typeof resultat.result, "string");
});

test("une erreur Python est retournée à TypeScript", async () => {
  const resultat = await executerAvecPython({
    name: "outil_inexistant",
    arguments: {},
  });

  assert.equal(resultat.success, false);
  assert.deepEqual(resultat.error, {
    type: "OutilInconnu",
    message: 'L outil "outil_inexistant" n existe pas.',
  });
});