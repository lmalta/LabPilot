import assert from "node:assert/strict";
import test from "node:test";

import { HistoriqueMessages } from "../src/historique.js";

test("un historique peut être créé vide", () => {
  const historique = new HistoriqueMessages();

  assert.deepEqual(historique.obtenir(), []);
});

test("un message peut être ajouté à l historique", () => {
  const historique = new HistoriqueMessages();

  historique.ajouter({
    role: "user",
    content: "Bonjour",
  });

  assert.deepEqual(historique.obtenir(), [
    {
      role: "user",
      content: "Bonjour",
    },
  ]);
});

test("l historique conserve plusieurs messages dans l ordre", () => {
  const historique = new HistoriqueMessages();

  historique.ajouter({
    role: "user",
    content: "Bonjour",
  });

  historique.ajouter({
    role: "assistant",
    content: "Bonjour !",
  });

  assert.deepEqual(historique.obtenir(), [
    {
      role: "user",
      content: "Bonjour",
    },
    {
      role: "assistant",
      content: "Bonjour !",
    },
  ]);
});

test("obtenir retourne une copie de l historique", () => {
  const historique = new HistoriqueMessages();

  historique.ajouter({
    role: "user",
    content: "Bonjour",
  });

  const messages = historique.obtenir();

  messages.push({
    role: "assistant",
    content: "Message externe",
  });

  assert.deepEqual(historique.obtenir(), [
    {
      role: "user",
      content: "Bonjour",
    },
  ]);
});

test("un historique peut être initialisé avec des messages", () => {
  const historique = new HistoriqueMessages([
    {
      role: "user",
      content: "Bonjour",
    },
    {
      role: "assistant",
      content: "Bonjour !",
    },
  ]);

  assert.deepEqual(historique.obtenir(), [
    {
      role: "user",
      content: "Bonjour",
    },
    {
      role: "assistant",
      content: "Bonjour !",
    },
  ]);
});
