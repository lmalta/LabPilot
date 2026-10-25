
import assert from "node:assert/strict";
import test from "node:test";

import { definitionsOutils } from "../src/labpilot.js";
import type { ToolExecution, ToolResult } from "../src/types.js";
import { executerOutil } from "../src/outils.js";
import { PontPython } from "../src/pont-python.js";

const outilsAttendus = [
  "heure_actuelle",
  "heure_dans",
  "etat_systeme",
  "etat_gpu",
  "etat_ollama",
  "etat_home_assistant",
  "etat_proxmox",
  "inventaire_os_proxmox",
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

test("l'outil etat_home_assistant est correctement défini", () => {
  const outil = definitionsOutils.find(
    (outil) => outil.function.name === "etat_home_assistant",
  );

  assert.ok(outil);
  assert.equal(outil.type, "function");
  assert.equal(outil.function.parameters.type, "object");
  assert.deepEqual(outil.function.parameters.required, []);
});

test("l'outil etat_proxmox est correctement défini", () => {
  const outil = definitionsOutils.find(
    (outil) => outil.function.name === "etat_proxmox",
  );

  assert.ok(outil);
  assert.equal(outil.type, "function");
  assert.equal(outil.function.parameters.type, "object");
});

test("le catalogue contient exactement les huit outils attendus", () => {
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

test("un outil connu peut être exécuté par Python", async () => {
  const pont = new PontPython();

  pont.démarrer();

  try {
    const resultat = await executerOutil(
      pont,
      {
        name: "heure_actuelle",
        arguments: {},
      },
    );

    assert.equal(resultat.success, true);
    assert.equal(typeof resultat.result, "string");
  } finally {
    pont.arrêter();
  }
});

test("un outil Python peut recevoir des arguments depuis TypeScript", async () => {
  const pont = new PontPython();

  pont.démarrer();

  try {
    const resultat = await executerOutil(
      pont,
      {
        name: "heure_dans",
        arguments: {
          minutes: 30,
        },
      },
    );

    assert.equal(resultat.success, true);
    assert.equal(typeof resultat.result, "string");
  } finally {
    pont.arrêter();
  }
});

test("un outil inconnu retourne une erreur", async () => {
  const pont = new PontPython();

  const resultat = await executerOutil(
    pont,
    {
      name: "outil_inexistant",
      arguments: {},
    },
  );

  assert.equal(resultat.success, false);
  assert.deepEqual(resultat.error, {
    type: "OutilInconnu",
    message: 'L outil "outil_inexistant" n existe pas.',
  });
});

test("un même pont Python peut exécuter plusieurs outils successivement", async () => {
  const pont = new PontPython();

  pont.démarrer();

  try {
    const premier = await pont.executer({
      name: "heure_actuelle",
      arguments: {},
    });

    const second = await pont.executer({
      name: "heure_dans",
      arguments: {
        minutes: 30,
      },
    });

    assert.equal(premier.success, true);
    assert.equal(typeof premier.result, "string");

    assert.equal(second.success, true);
    assert.equal(typeof second.result, "string");
  } finally {
    pont.arrêter();
  }
});

test("le pont Python refuse une exécution avant son démarrage", async () => {
  const pont = new PontPython();

  await assert.rejects(
    pont.executer({
      name: "heure_actuelle",
      arguments: {},
    }),
    {
      message: "Le pont Python n est pas démarré.",
    },
  );
});

test("le pont Python refuse une deuxième exécution pendant une exécution en attente", async () => {
  const pont = new PontPython();

  pont.démarrer();

  try {
    const premiere = pont.executer({
      name: "heure_actuelle",
      arguments: {},
    });

    await assert.rejects(
      pont.executer({
        name: "heure_dans",
        arguments: {
          minutes: 30,
        },
      }),
      {
        message: "Une exécution Python est déjà en attente.",
      },
    );

    const resultat = await premiere;

    assert.equal(resultat.success, true);
  } finally {
    pont.arrêter();
  }
});

test("le pont Python peut être redémarré après un arrêt", async () => {
  const pont = new PontPython();

  pont.démarrer();

  const premier = await pont.executer({
    name: "heure_actuelle",
    arguments: {},
  });

  assert.equal(premier.success, true);

  pont.arrêter();

  pont.démarrer();

  try {
    const second = await pont.executer({
      name: "heure_dans",
      arguments: {
        minutes: 30,
      },
    });

    assert.equal(second.success, true);
    assert.equal(typeof second.result, "string");
  } finally {
    pont.arrêter();
  }
});

test("le pont Python signale l arrêt du processus pendant une exécution", async () => {
  const pont = new PontPython();

  pont.démarrer();

  const execution = pont.executer({
    name: "heure_actuelle",
    arguments: {},
  });

  pont.arrêter();

  await assert.rejects(
    execution,
    /Le processus Python a été arrêté pendant une exécution\./,
  );
});