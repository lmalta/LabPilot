
import assert from "node:assert/strict";
import test from "node:test";

import { definitionsOutils } from "../src/labpilot.js";

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
