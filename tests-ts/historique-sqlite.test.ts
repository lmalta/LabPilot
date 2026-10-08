import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import test from "node:test";
import assert from "node:assert/strict";

import {
  HistoriqueMessages,
} from "../src/historique.js";
import {
  DepotConversationsSQLite,
} from "../src/depot-conversations-sqlite.js";

test("un historique persiste réellement dans SQLite", () => {
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

  const historique =
    new HistoriqueMessages();

  historique.ajouter({
    role: "user",
    content: "Bonjour LabPilot",
  });

  historique.ajouter({
    role: "assistant",
    content: "Bonjour !",
  });

  historique.sauvegarder(
    premierDepot,
    conversation.id,
  );

  premierDepot.fermer();

  const secondDepot =
    new DepotConversationsSQLite(chemin);

  const recharge =
    HistoriqueMessages.charger(
      secondDepot,
      conversation.id,
    );

  assert.deepEqual(
    recharge.obtenir(),
    historique.obtenir(),
  );

  secondDepot.fermer();

  rmSync(dossier, {
    recursive: true,
    force: true,
  });
});
