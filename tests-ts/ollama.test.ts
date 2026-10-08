import assert from "node:assert/strict";
import test from "node:test";
import { PontPython } from "../src/pont-python.js";
import { executerOutil } from "../src/outils.js";
import { convertirResultatEnMessageOutil, convertirToolCallEnExecution, OllamaClient } from "../src/ollama.js";
import { Orchestrateur } from "../src/orchestrateur.js";

test("Ollama demande l utilisation d un outil", async () => {
  const ollama = new OllamaClient();

  const message = await ollama.chat([
    {
      role: "user",
      content: "Donne-moi l état actuel du système.",
    },
  ]);

  assert.equal(message.role, "assistant");
  assert.ok(
    message.tool_calls !== undefined,
    "Ollama doit demander l utilisation d un outil.",
  );
  assert.ok(message.tool_calls.length > 0);
  assert.equal(
    message.tool_calls[0]?.function.name,
    "etat_systeme",
  );
});

test("Ollama retourne une réponse finale", async () => {
  const ollama = new OllamaClient();

  const message = await ollama.chat([
    {
      role: "user",
      content: "Réponds uniquement par le mot OK.",
    },
  ]);

  assert.equal(message.role, "assistant");
  assert.equal(typeof message.content, "string");
  assert.notEqual(message.content.length, 0);
});

test("Ollama transmet les arguments d un outil", async () => {
  const ollama = new OllamaClient();

  const message = await ollama.chat([
    {
      role: "user",
      content:
        "Quelle heure sera-t-il dans exactement 30 minutes ? Utilise l outil heure_dans.",
    },
  ]);

  assert.equal(message.role, "assistant");
  assert.ok(
    message.tool_calls !== undefined,
    "Ollama doit demander l utilisation d un outil.",
  );
  assert.ok(message.tool_calls.length > 0);

  const appel = message.tool_calls[0];

  assert.ok(appel !== undefined);
  assert.equal(appel.function.name, "heure_dans");
  assert.equal(appel.function.arguments["minutes"], 30);
});

test("Un appel d outil Ollama devient une exécution LabPilot", () => {
  const appel = {
    function: {
      name: "heure_dans",
      arguments: {
        minutes: 30,
      },
    },
  };

  const execution = convertirToolCallEnExecution(appel);

  assert.deepEqual(execution, {
    name: "heure_dans",
    arguments: {
      minutes: 30,
    },
  });
});

test("Un outil demandé par Ollama peut être exécuté par LabPilot", async () => {
  const ollama = new OllamaClient();
  const pont = new PontPython();

  pont.démarrer();

  try {
    const message = await ollama.chat([
      {
        role: "user",
        content: "Donne-moi l état actuel du système.",
      },
    ]);

    assert.equal(message.role, "assistant");
    assert.ok(message.tool_calls !== undefined);
    assert.ok(message.tool_calls.length > 0);

    const appel = message.tool_calls[0];

    assert.ok(appel !== undefined);

    const execution = convertirToolCallEnExecution(appel);
    const resultat = await executerOutil(pont, execution);

    assert.equal(resultat.success, true);
    assert.ok(resultat.result !== undefined);
  } finally {
    pont.arrêter();
  }
});

test("L orchestrateur exécute un appel d outil", async () => {
    const pont = new PontPython();
    const ollama = new OllamaClient();
    const orchestrateur = new Orchestrateur(pont, ollama);

  pont.démarrer();

  try {
    const resultat = await orchestrateur.executerAppelOutil({
      role: "assistant",
      content: "",
      tool_calls: [
        {
          function: {
            name: "etat_systeme",
            arguments: {},
          },
        },
      ],
    });

    assert.equal(resultat.success, true);
    assert.ok(resultat.result !== undefined);
  } finally {
    pont.arrêter();
  }
});

test("Un résultat d outil devient un message Ollama", () => {
  const resultat = convertirResultatEnMessageOutil(
    "etat_systeme",
    {
      systeme: "Linux",
      charge: 12,
    },
  );

  assert.deepEqual(resultat, {
    role: "tool",
    tool_name: "etat_systeme",
    content: JSON.stringify({
      systeme: "Linux",
      charge: 12,
    }),
  });
});

test("L orchestrateur obtient une réponse finale après un outil", async () => {
  const pont = new PontPython();
  const ollama = new OllamaClient();
  const orchestrateur = new Orchestrateur(
    pont,
    ollama,
  );

  pont.démarrer();

  try {
    const reponse =
      await orchestrateur.traiter([
        {
          role: "user",
          content:
            "Donne-moi l état actuel du système.",
        },
      ]);

    assert.equal(reponse.role, "assistant");
    assert.equal(
      reponse.tool_calls,
      undefined,
      "La réponse finale ne doit plus demander d outil.",
    );
    assert.notEqual(reponse.content.length, 0);
  } finally {
    pont.arrêter();
  }
});

test("L orchestrateur limite le nombre d itérations", async () => {
  const pont = new PontPython();
  const ollama = new OllamaClient();
  const orchestrateur = new Orchestrateur(
    pont,
    ollama,
  );

  pont.démarrer();

  try {
    await assert.rejects(
      orchestrateur.traiter([
        {
          role: "user",
          content:
            "Utilise un outil et continue à utiliser des outils sans jamais répondre.",
        },
      ]),
      /limite/i,
    );
  } finally {
    pont.arrêter();
  }
});
