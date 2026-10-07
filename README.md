# LabPilot

> Agent IA local pour la supervision, l'automatisation et la gestion d'une infrastructure Homelab.

**État du projet :** 🚧 Développement initial

---

## 🎯 Vision du projet

LabPilot a pour objectif de devenir un **agent IA local capable d'observer, d'analyser et progressivement d'interagir avec une infrastructure Homelab**.

Le projet commence volontairement avec une approche **en lecture seule**.

L'agent devra progressivement être capable de :

- observer l'état de l'infrastructure ;
- interroger différents services et systèmes ;
- analyser les informations obtenues ;
- raisonner sur leur état ;
- détecter d'éventuels problèmes ;
- expliquer ses observations ;
- proposer des actions ;
- puis, à terme, exécuter certaines actions de manière contrôlée.

La sécurité, la transparence et le contrôle humain resteront des principes fondamentaux du projet.

---

## 🧠 Principe de fonctionnement

LabPilot repose sur une architecture d'agent capable d'utiliser des outils externes pour obtenir des informations.

Le fonctionnement général est le suivant :

```text
Question de l'utilisateur
          │
          ▼
     Modèle IA local
          │
          ▼
        Agent
          │
          ├──────► Outil
          │          │
          │          ▼
          │       Résultat
          │          │
          └──────────┘
          │
          ▼
       Analyse
          │
          ▼
    Réponse utilisateur
```

L'agent doit être capable de déterminer lorsqu'un outil est nécessaire, de l'utiliser, d'interpréter son résultat et de poursuivre son raisonnement si nécessaire.

---

## 🏗️ Architecture initiale

La première version de LabPilot sera volontairement simple.

```text
                         LabPilot
                            │
                     ┌──────┴──────┐
                     │    Agent    │
                     └──────┬──────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
           Système         GPU          Ollama
            outils        outils          API
```

Les premiers outils seront exclusivement destinés à la **lecture et à l'observation**.

Les premières capacités prévues sont :

- état du système ;
- état du GPU ;
- état d'Ollama ;
- modèles disponibles ;
- informations générales sur l'environnement.

De nouvelles intégrations seront ajoutées progressivement.

---

## 🔒 Sécurité

LabPilot est conçu dès le départ avec l'objectif de pouvoir devenir un projet public sur GitHub.

Le dépôt ne doit donc jamais contenir :

- mot de passe ;
- clé API ;
- jeton d'accès ;
- clé privée ;
- adresse IP interne réelle ;
- nom d'hôte interne sensible ;
- identifiant ou mot de passe intégré dans une URL ;
- information personnelle ;
- information spécifique permettant d'identifier ou de compromettre l'infrastructure réelle.

Les informations propres à une installation doivent rester en dehors du dépôt.

Elles pourront être fournies par :

- variables d'environnement ;
- fichiers de configuration locaux ignorés par Git ;
- mécanismes de gestion de secrets adaptés à l'environnement d'exécution.

Exemple :

```text
OLLAMA_URL=http://<ADRESSE_OLLAMA>:11434
HOME_ASSISTANT_URL=http://<ADRESSE_HOME_ASSISTANT>:8123
HOME_ASSISTANT_TOKEN=<VOTRE_JETON>
```

### Principe fondamental

> **Tout ce qui est commité dans LabPilot doit pouvoir être rendu public sans nettoyage préalable.**

---

## 🧪 Méthode de développement

LabPilot sera développé progressivement.

Chaque fonctionnalité suivra autant que possible le cycle :

```text
Conception
    ↓
Développement
    ↓
Test
    ↓
Validation
    ↓
Documentation
    ↓
Commit Git
```

Chaque composant important sera testé indépendamment avant son intégration au fonctionnement global de l'agent.

L'objectif est de conserver un projet :

- simple à comprendre ;
- modulaire ;
- testable ;
- documenté ;
- sécurisé ;
- facilement évolutif.

---

## 🗺️ Feuille de route

### Phase 1 — Fondations

- [x] Créer le dépôt GitHub
- [x] Définir le nom du projet
- [x] Définir le périmètre initial
- [x] Définir les principes de sécurité
- [ ] Créer la structure de l'agent
- [ ] Définir la gestion de la configuration
- [ ] Mettre en place la communication avec le modèle IA

### Phase 2 — Premier agent en lecture seule

- [ ] Mettre en place la boucle de fonctionnement de l'agent
- [ ] Mettre en place l'exécution des outils
- [ ] Créer l'outil d'état du système
- [ ] Créer l'outil d'état du GPU
- [ ] Créer l'outil d'état d'Ollama
- [ ] Tester le choix automatique des outils
- [ ] Tester le raisonnement à partir des résultats

### Phase 3 — Intégration du Homelab

- [ ] Intégrer Home Assistant
- [ ] Intégrer Proxmox
- [ ] Ajouter des outils réseau
- [ ] Ajouter des outils de stockage
- [ ] Ajouter des outils de supervision
- [ ] Améliorer les rapports d'état

### Phase 4 — Automatisation contrôlée

- [ ] Définir les actions autorisées
- [ ] Mettre en place les demandes de confirmation
- [ ] Journaliser les actions
- [ ] Définir les permissions
- [ ] Tester les erreurs et les situations de récupération
- [ ] Empêcher les actions dangereuses non confirmées

### Phase 5 — Architecture de production

- [ ] Séparer LabPilot du serveur de modèle IA
- [ ] Déployer LabPilot comme service indépendant
- [ ] Conteneuriser l'application
- [ ] Étudier un déploiement K3s
- [ ] Améliorer la supervision
- [ ] Renforcer la sécurité

---

## 📁 Structure du projet

La structure initiale sera volontairement réduite.

Elle évoluera avec les fonctionnalités du projet.

```text
LabPilot/
├── README.md
├── .gitignore
├── agent/
├── tests/
└── ...
```

---

## 🤖 Modèle IA local

LabPilot est conçu pour fonctionner avec des modèles IA hébergés localement.

L'environnement initial utilise **Ollama** comme moteur d'exécution des modèles.

L'agent communiquera avec le moteur IA par API afin de conserver une séparation claire entre :

- le modèle IA ;
- le moteur d'exécution ;
- la logique de l'agent ;
- les outils disponibles.

Cette séparation permettra de faire évoluer le modèle utilisé sans devoir modifier l'architecture générale de LabPilot.

---

## 🏠 Infrastructure cible

LabPilot est destiné à pouvoir interagir avec différents composants d'un Homelab, notamment :

- Home Assistant ;
- Proxmox ;
- serveurs Linux ;
- serveurs GPU ;
- serveurs de modèles IA locaux ;
- services réseau ;
- stockage ;
- systèmes de supervision.

Les informations spécifiques à l'infrastructure réelle ne seront jamais intégrées au dépôt.

---

## 🔄 Évolution prévue

LabPilot commence comme un agent d'observation.

L'évolution recherchée est progressivement :

```text
Observer
   ↓
Comprendre
   ↓
Raisonner
   ↓
Proposer
   ↓
Demander confirmation
   ↓
Agir
   ↓
Vérifier
   ↓
Rendre compte
```

L'objectif n'est donc pas simplement de créer un chatbot capable de répondre à des questions sur le Homelab, mais de construire progressivement un **véritable agent capable d'utiliser son environnement comme source d'information et comme ensemble d'outils**.

---

## 📌 État actuel

LabPilot dispose maintenant de son premier socle fonctionnel.

Le projet sait actuellement :

- charger sa configuration depuis un fichier `.env` ;
- définir l'URL et le modèle Ollama utilisés ;
- communiquer avec l'API `/api/chat` d'Ollama ;
- encapsuler la communication avec le LLM dans un module dédié ;
- maintenir un historique de conversation dans un objet `Agent` ;
- transmettre cet historique au LLM à chaque nouvelle requête ;
- conserver les réponses du LLM dans l'historique ;
- exécuter une première boucle simple utilisateur → agent → LLM → réponse.

L'architecture commence également à être séparée en plusieurs responsabilités :

```text
labpilot.py
    ↓
Agent
    ↓
Ollama
    ↓
LLM local

avec une configuration indépendante :

.env
    ↓
configuration.py
    ↓
Agent / Ollama
---

## 📄 Licence

La licence du projet sera définie ultérieurement.

---

## 🤝 Contribution

Les règles de contribution seront définies lorsque l'architecture initiale du projet sera stabilisée.