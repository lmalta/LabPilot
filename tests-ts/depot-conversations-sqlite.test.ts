import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

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