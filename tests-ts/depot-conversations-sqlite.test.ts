import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";
import Database from "better-sqlite3";

import { DepotConversationsSQLite } from "../src/depot-conversations-sqlite.js";

test("une conversation peut être créée dans SQLite", () => {
  const dossier = mkdtempSync(
    join(tmpdir(), "labpilot-"),
  );

  const chemin = join(
    dossier,
    "labpilot.db",
  );

  const depot =
    new DepotConversationsSQLite(chemin);

  const conversation =
    depot.creerConversation();

  assert.match(
    conversation.id,
    /^[0-9a-f-]{36}$/,
  );

  assert.ok(conversation.creeLe);

  const relue =
    depot.obtenirConversation(
      conversation.id,
    );

  assert.deepEqual(
    relue,
    conversation,
  );

  depot.fermer();

  rmSync(dossier, {
    recursive: true,
    force: true,
  });
});

test("un message peut être ajouté à une conversation SQLite", () => {
  const dossier = mkdtempSync(
    join(tmpdir(), "labpilot-"),
  );

  const chemin = join(
    dossier,
    "labpilot.db",
  );

  const depot =
    new DepotConversationsSQLite(chemin);

  const conversation =
    depot.creerConversation();

  depot.ajouterMessage(
    conversation.id,
    {
      role: "user",
      content: "Bonjour LabPilot",
    },
  );

  const messages =
    depot.obtenirMessages(
      conversation.id,
    );

  assert.deepEqual(
    messages,
    [
      {
        role: "user",
        content: "Bonjour LabPilot",
      },
    ],
  );

  depot.fermer();

  rmSync(dossier, {
    recursive: true,
    force: true,
  });
});

test("les conversations peuvent être listées depuis SQLite", () => {
  const dossier = mkdtempSync(
    join(tmpdir(), "labpilot-"),
  );

  const chemin = join(
    dossier,
    "labpilot.db",
  );

  const depot =
    new DepotConversationsSQLite(chemin);

  const premiere =
    depot.creerConversation();

  const deuxieme =
    depot.creerConversation();

  const conversations =
    depot.listerConversations();

  assert.equal(
    conversations.length,
    2,
  );

  assert.deepEqual(
    conversations[0],
    premiere,
  );

  assert.deepEqual(
    conversations[1],
    deuxieme,
  );

  depot.fermer();

  rmSync(dossier, {
    recursive: true,
    force: true,
  });
});

test("les différents types de messages sont conservés dans l ordre", () => {
  const dossier = mkdtempSync(
    join(tmpdir(), "labpilot-"),
  );

  const chemin = join(
    dossier,
    "labpilot.db",
  );

  const depot =
    new DepotConversationsSQLite(chemin);

  const conversation =
    depot.creerConversation();

  depot.ajouterMessage(
    conversation.id,
    {
      role: "user",
      content: "Quel est l état du système ?",
    },
  );

  depot.ajouterMessage(
    conversation.id,
    {
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
    },
  );

  depot.ajouterMessage(
    conversation.id,
    {
      role: "tool",
      content: '{"cpu": 12}',
      tool_name: "etat_systeme",
    },
  );

  depot.ajouterMessage(
    conversation.id,
    {
      role: "assistant",
      content: "Le système fonctionne normalement.",
    },
  );

  const messages =
    depot.obtenirMessages(
      conversation.id,
    );

  assert.deepEqual(
    messages,
    [
      {
        role: "user",
        content: "Quel est l état du système ?",
      },
      {
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
      },
      {
        role: "tool",
        content: '{"cpu": 12}',
        tool_name: "etat_systeme",
      },
      {
        role: "assistant",
        content: "Le système fonctionne normalement.",
      },
    ],
  );

  depot.fermer();

  rmSync(dossier, {
    recursive: true,
    force: true,
  });
});

test("les conversations persistent après fermeture et réouverture de SQLite", () => {
  const dossier = mkdtempSync(
    join(tmpdir(), "labpilot-"),
  );

  const chemin = join(
    dossier,
    "labpilot.db",
  );

  const premierDepot =
    new DepotConversationsSQLite(chemin);

  const conversation =
    premierDepot.creerConversation();

  premierDepot.ajouterMessage(
    conversation.id,
    {
      role: "user",
      content: "Message persistant",
    },
  );

  premierDepot.fermer();

  const secondDepot =
    new DepotConversationsSQLite(chemin);

  const conversationRelue =
    secondDepot.obtenirConversation(
      conversation.id,
    );

  const messagesRelus =
    secondDepot.obtenirMessages(
      conversation.id,
    );

  assert.deepEqual(
    conversationRelue,
    conversation,
  );

  assert.deepEqual(
    messagesRelus,
    [
      {
        role: "user",
        content: "Message persistant",
      },
    ],
  );

  secondDepot.fermer();

  rmSync(dossier, {
    recursive: true,
    force: true,
  });
});

test("une ancienne base SQLite est migrée sans perdre son historique", () => {
  const dossier = mkdtempSync(join(tmpdir(), "labpilot-migration-"));
  const chemin = join(dossier, "labpilot.db");

  const ancienneBase = new Database(chemin);

  ancienneBase.exec(`
    CREATE TABLE conversations (
      id TEXT PRIMARY KEY,
      cree_le TEXT NOT NULL
    );

    CREATE TABLE messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      conversation_id TEXT NOT NULL,
      ordre INTEGER NOT NULL,
      role TEXT NOT NULL,
      contenu TEXT NOT NULL,
      nom_outil TEXT,
      FOREIGN KEY (conversation_id)
        REFERENCES conversations(id)
        ON DELETE CASCADE
    );

    CREATE INDEX idx_messages_conversation_ordre
      ON messages(conversation_id, ordre);

    INSERT INTO conversations (id, cree_le)
    VALUES ('ancienne-conversation', '2026-01-01T00:00:00.000Z');

    INSERT INTO messages (conversation_id, ordre, role, contenu)
    VALUES ('ancienne-conversation', 0, 'user', 'Historique existant');
  `);

  ancienneBase.close();

  const depot = new DepotConversationsSQLite(chemin);

  assert.deepEqual(
    depot.obtenirMessages("ancienne-conversation"),
    [{ role: "user", content: "Historique existant" }],
  );

  depot.ajouterMessage("ancienne-conversation", {
    role: "assistant",
    content: "",
    tool_calls: [{
      function: {
        name: "etat_systeme",
        arguments: {},
      },
    }],
  });

  const messages = depot.obtenirMessages("ancienne-conversation");

  assert.equal(messages.length, 2);
  assert.deepEqual(messages[1], {
    role: "assistant",
    content: "",
    tool_calls: [{
      function: {
        name: "etat_systeme",
        arguments: {},
      },
    }],
  });

  depot.fermer();
  rmSync(dossier, { recursive: true, force: true });
});
