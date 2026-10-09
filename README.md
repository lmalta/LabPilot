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
- informations générales sur l'environnement ;
- limiter le nombre de cycles successifs d'appels d'outils pour empêcher les boucles incontrôlées ;
- consulter l'état des GPU NVIDIA visibles par le système ;
- consulter l'état du serveur Ollama, sa version, les modèles disponibles et les modèles actuellement actifs ;
- interpréter les résultats des outils et les utiliser pour formuler une réponse.

De nouvelles intégrations seront ajoutées progressivement.

---

## 🧩 Architecture logicielle

LabPilot adopte progressivement une architecture mixte **TypeScript / Python**.

TypeScript et Node.js seront progressivement utilisés pour les composants liés à :

- l'orchestration de l'agent ;
- les API ;
- les outils ;
- les communications WebSocket ;
- la future interface web ;
- les composants nécessitant une forte intégration avec l'écosystème JavaScript/TypeScript.

Python reste privilégié pour les composants liés à :

- l'IA et aux services de modèles ;
- PyTorch et CUDA ;
- le traitement documentaire ;
- les calculs et traitements scientifiques ;
- les composants exploitant directement l'écosystème Python.

Cette évolution se fera progressivement, par fonctionnalités indépendantes et validées.

LabPilot ne sera donc pas réécrit brutalement dans un autre langage. L'objectif est d'introduire TypeScript là où il apporte une réelle valeur, tout en conservant Python pour les domaines où son écosystème est particulièrement adapté.

### Premier socle TypeScript

Le projet dispose désormais d'un premier socle TypeScript, destiné à accueillir progressivement les composants d'orchestration de LabPilot.

```text
src/
├── index.ts
├── labpilot.ts
└── types.ts

       │
       ▼

    TypeScript
       │
       ▼
      tsc
       │
       ▼
     dist/
```

Le premier composant introduit définit les types utilisés pour représenter les messages échangés par l'agent :

- messages système ;
- messages utilisateur ;
- réponses de l'assistant ;
- messages provenant des outils ;
- appels d'outils.

Ces types constituent un premier contrat commun pour les futurs composants TypeScript de LabPilot.

### Catalogue TypeScript des outils

Le projet dispose également d'un catalogue TypeScript décrivant les outils disponibles pour l'agent.

Les définitions actuelles correspondent aux cinq outils existants côté Python :

- `heure_actuelle` ;
- `heure_dans` ;
- `etat_systeme` ;
- `etat_gpu` ;
- `etat_ollama`.

TypeScript décrit ainsi le contrat des outils sans remplacer leur implémentation Python.

Cette séparation permet d'introduire progressivement TypeScript dans l'orchestration de LabPilot tout en conservant Python pour l'exécution des composants déjà existants.

### Tests TypeScript

Les tests TypeScript utilisent le module de test natif de Node.js.

Le catalogue des outils est notamment vérifié afin de s'assurer que les cinq outils attendus sont bien présents.

Les vérifications TypeScript peuvent être effectuées avec :

```bash
npm run typecheck
```

La compilation du projet est effectuée avec :

```bash
npm run build
```

Les tests TypeScript sont exécutés avec :

```bash
npm run test:ts
```

Cette commande compile d'abord le projet puis exécute les tests TypeScript compilés.

Les fichiers générés dans `dist/` ainsi que les dépendances installées dans `node_modules/` ne sont pas versionnés.

Les données locales de LabPilot sont également exclues du dépôt Git.

Les dépendances Python restent gérées dans `requirements.txt`, tandis que les dépendances Node.js/TypeScript sont gérées dans `package.json` et `package-lock.json`.

### Pont TypeScript → Python persistant

Le pont entre TypeScript et Python repose maintenant sur un processus Python persistant.

TypeScript démarre le processus Python une seule fois, puis peut lui transmettre plusieurs demandes d'exécution successives sans recréer le processus à chaque appel.

```text
TypeScript
   │
   ▼
PontPython
   │
   ├── démarrer()
   │
   ├── executer(outil 1) ──┐
   ├── executer(outil 2) ──┤
   ├── executer(outil 3) ──┤
   │                        │
   │                   processus Python
   │                        │
   └── arrêter() ───────────┘
```

La communication utilise un protocole simple basé sur JSON :

- une requête JSON par ligne ;
- une réponse JSON par ligne ;
- les arguments de l'outil sont transmis dans la requête ;
- le résultat ou l'erreur est retourné dans la réponse.

Le cycle de vie du pont est contrôlé par trois opérations :

- `démarrer()` démarre le processus Python ;
- `executer()` transmet une exécution d'outil et attend sa réponse ;
- `arrêter()` termine le processus Python.

L'exécution des outils depuis TypeScript utilise directement ce pont persistant.

La fonction `executerOutil()` reçoit une instance de `PontPython` et lui transmet la demande d'exécution. Elle vérifie d'abord que l'outil demandé existe dans le catalogue TypeScript, puis délègue son exécution au processus Python.

Le cycle d'exécution est donc le suivant :

```text
TypeScript
   │
   ▼
executerOutil()
   │
   ├── vérification de l'outil
   │
   ▼
PontPython.executer()
   │
   ▼
processus Python persistant
   │
   ▼
outil Python réel
   │
   ▼
ToolResult
```

Les exécutions sont actuellement **séquentielles** : une seule demande peut être en attente à la fois. Une deuxième exécution lancée avant la réception de la première réponse est refusée explicitement.

Le pont gère également les erreurs de communication et l'arrêt du processus Python. Après un arrêt, le pont peut être démarré à nouveau et utilisé pour de nouvelles exécutions.

Cette architecture permet à TypeScript de devenir progressivement l'orchestrateur principal de LabPilot tout en conservant Python pour l'exécution des outils et les futurs services liés à l'IA, au traitement documentaire et au calcul.

### Orchestration TypeScript

L'orchestration de l'agent est maintenant prise en charge par TypeScript.

Le rôle de TypeScript est de coordonner les échanges entre l'utilisateur, le modèle Ollama et les outils exécutés par Python.

Le cycle d'orchestration est le suivant :

```text
Utilisateur
   │
   ▼
Orchestrateur TypeScript
   │
   ▼
Ollama
   │
   ├── réponse finale ───────────────► Utilisateur
   │
   └── demande d'outil
           │
           ▼
      executerOutil()
           │
           ▼
       PontPython
           │
           ▼
       outil Python
           │
           ▼
       ToolResult
           │
           ▼
    message d'outil
           │
           ▼
       historique
           │
           ▼
         Ollama
           │
           └── ...
```

`OllamaClient` est responsable de la communication avec l'API Ollama. Il transmet au modèle l'historique des messages ainsi que le catalogue des outils disponibles.

`Orchestrateur` est responsable de la boucle d'exécution. Il analyse la réponse du modèle pour déterminer si celui-ci demande l'utilisation d'un outil ou s'il fournit directement une réponse finale.

Lorsqu'un outil est demandé, TypeScript :

1. convertit l'appel du modèle en `ToolExecution` ;
2. transmet l'exécution à `executerOutil()` ;
3. récupère le `ToolResult` fourni par Python ;
4. transforme le résultat en message d'outil ;
5. ajoute la réponse du modèle et le résultat à l'historique ;
6. renvoie l'historique mis à jour à Ollama.

Cette boucle permet au modèle de demander plusieurs outils successivement avant de produire sa réponse finale.

Une limite de **10 itérations d'orchestration** est appliquée. Si le modèle continue à demander des outils après cette limite, l'orchestrateur arrête l'exécution et retourne une erreur contrôlée.

Cette limite constitue une protection contre les boucles d'appels d'outils incontrôlées.

La responsabilité des composants est ainsi séparée :

```text
TypeScript
├── orchestration de l'agent
├── communication avec Ollama
├── historique des messages
├── détection des appels d'outils
├── contrôle de la boucle
└── limite d'itérations

Python
├── exécution des outils
├── PyTorch / CUDA
├── traitement documentaire
└── futurs services IA et calcul
```

TypeScript ne dépend pas de l'implémentation interne des outils Python. Il manipule uniquement les structures `ToolExecution` et `ToolResult` ainsi que le catalogue des outils.

Cette séparation permet de faire évoluer progressivement LabPilot vers une architecture dans laquelle TypeScript constitue l'orchestrateur principal, tandis que Python reste spécialisé dans l'exécution des outils et les traitements nécessitant son écosystème.

### Historique des messages TypeScript

La gestion de l'historique des messages est centralisée dans le composant `HistoriqueMessages`.

L'historique peut être conservé en mémoire et persisté dans un dépôt de conversations. Cette séparation permet à l'orchestrateur de manipuler l'historique sans dépendre directement de SQLite.

L'architecture de persistance est organisée ainsi :

```text
HistoriqueMessages
        │
        ▼
DepotConversations
        │
        ▼
DepotConversationsSQLite
        │
        ▼
     SQLite
```

`DepotConversations` définit l'interface du dépôt. `DepotConversationsSQLite` en fournit actuellement l'implémentation avec une base SQLite locale.

`HistoriqueMessages` permet :

- d'initialiser un historique avec des messages existants ;
- d'ajouter de nouveaux messages ;
- de récupérer une copie de l'historique sans exposer directement son état interne ;
- de sauvegarder les nouveaux messages dans un dépôt ;
- de recharger un historique existant depuis un dépôt ;
- d'éviter de sauvegarder plusieurs fois les mêmes messages lors de sauvegardes successives.

La base SQLite utilisée par défaut est stockée dans :

```text
data/labpilot.db
```

Le répertoire `data/` est exclu du dépôt Git afin que les données locales des conversations ne soient jamais versionnées.

L'orchestrateur peut également utiliser un `HistoriqueMessages` déjà existant. Cela permet de recharger une conversation persistée avant de poursuivre son traitement.

Lorsqu'un outil est utilisé, l'historique conserve notamment :

```text
message utilisateur
        │
        ▼
réponse Ollama avec appel d'outil
        │
        ▼
résultat de l'outil
        │
        ▼
nouvel appel Ollama
        │
        ▼
réponse finale
```

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
- [x] Créer la structure initiale du projet
- [x] Mettre en place la gestion de la configuration
- [x] Mettre en place la communication avec le modèle IA local
- [x] Séparer la logique de l'agent de la communication avec Ollama
- [x] Mettre en place un historique de conversation

### Phase 2 — Premier agent en lecture seule

- [x] Mettre en place la boucle de fonctionnement de l'agent
- [x] Définir le mécanisme de déclaration des outils
- [x] Permettre au modèle de demander l'utilisation d'un outil
- [x] Mettre en place l'exécution des outils
- [x] Permettre la transmission d'arguments aux outils
- [x] Renvoyer le résultat d'un outil au modèle
- [x] Générer une réponse finale à partir du résultat de l'outil
- [x] Tester le choix automatique des outils
- [x] Tester le fonctionnement des outils avec l'historique de conversation
- [x] Créer l'outil d'état du système
- [x] Créer l'outil d'état du GPU
- [x] Créer l'outil d'état d'Ollama
- [x] Tester le raisonnement à partir des résultats
- [x] Gérer plusieurs appels d'outils successifs
- [x] Gérer les erreurs d'exécution des outils
- [x] Empêcher les boucles d'appels d'outils incontrôlées

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

La structure actuelle du projet évolue progressivement avec l'intégration de TypeScript.

```text
LabPilot/
├── src/
│   ├── index.ts
│   ├── labpilot.ts
│   ├── types.ts
│   ├── historique.ts
│   ├── orchestrateur.ts
│   ├── ollama-client.ts
│   ├── pont-python.ts
│   ├── depot-conversations.ts
│   ├── depot-conversations-sqlite.ts
│   └── ...
├── tests-ts/
│   └── ...
├── data/
│   └── labpilot.db
├── package.json
├── package-lock.json
├── requirements.txt
└── README.md
```

Le répertoire `data/` contient les données locales de LabPilot et n'est pas versionné.

Les fichiers TypeScript de `src/` contiennent progressivement les composants d'orchestration et les contrats utilisés par l'agent.

Les fichiers de `tests-ts/` contiennent les tests des composants TypeScript.

Les composants Python restent utilisés pour l'exécution des outils et les traitements spécialisés.

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

LabPilot dispose maintenant de son premier socle fonctionnel et de son premier mécanisme d'utilisation d'outils.

Le projet sait actuellement :

- charger sa configuration depuis un fichier `.env` ;
- définir l'URL et le modèle Ollama utilisés ;
- communiquer avec l'API `/api/chat` d'Ollama ;
- encapsuler la communication avec le LLM dans un module dédié ;
- maintenir un historique de conversation dans un objet `HistoriqueMessages` ;
- transmettre cet historique au LLM à chaque nouvelle requête ;
- conserver les réponses du LLM dans l'historique ;
- déclarer des outils utilisables par le modèle ;
- détecter lorsqu'Ollama demande l'utilisation d'un outil ;
- récupérer les arguments transmis par le modèle ;
- exécuter l'outil correspondant ;
- transmettre le résultat de l'outil au LLM ;
- générer une réponse finale à partir du résultat obtenu ;
- gérer plusieurs appels d'outils dans une même réponse du modèle ;
- enchaîner plusieurs séries d'appels d'outils jusqu'à obtenir une réponse finale ;
- capturer les erreurs d'exécution des outils et les transmettre au modèle ;
- conserver les appels d'outils et leurs résultats dans l'historique en mémoire ;
- persister l'historique des conversations dans une base SQLite locale ;
- recharger une conversation persistée depuis SQLite ;
- éviter la duplication des messages lors de sauvegardes successives ;
- présenter les résultats techniques de manière naturelle à l'utilisateur.

Un premier ensemble d'outils permet actuellement de travailler avec l'heure courante, de calculer une heure future et d'obtenir l'état général du système.

L'outil d'état du système fournit notamment :

- le nom de la machine ;
- le système d'exploitation ;
- la version du noyau ;
- l'architecture ;
- le nombre de CPU ;
- la mémoire totale et disponible ;
- les charges moyennes du système sur 1, 5 et 15 minutes.

Les charges moyennes correspondent au **load average Linux** et ne sont pas exprimées en pourcentage d'utilisation CPU.

L'architecture actuelle est organisée autour de plusieurs responsabilités :

```text
TypeScript
   │
   ├── Orchestrateur
   │       │
   │       ├── HistoriqueMessages
   │       │       │
   │       │       └── DepotConversations
   │       │               │
   │       │               └── DepotConversationsSQLite
   │       │
   │       ├── OllamaClient
   │       │
   │       └── PontPython
   │               │
   │               ▼
   │          processus Python
   │               │
   │               ▼
   │          outils Python
   │
   ▼
Ollama
```

La persistance des conversations est désormais organisée autour d'une interface de dépôt afin que l'orchestrateur ne dépende pas directement de SQLite.

Cette séparation permettra notamment de faire évoluer ultérieurement le mécanisme de stockage sans modifier la logique de l'orchestrateur.

La communication avec le modèle reste séparée de la logique de l'agent :

```text
Orchestrateur
   ↓
OllamaClient
   ↓
API Ollama
   ↓
LLM local
```

La communication avec les outils reste également séparée :

```text
Orchestrateur
   ↓
executerOutil()
   ↓
PontPython
   ↓
outil Python
   ↓
ToolResult
```

et la persistance des conversations :

```text
HistoriqueMessages
   ↓
DepotConversations
   ↓
DepotConversationsSQLite
   ↓
SQLite
```

Cette organisation permet à chaque composant d'avoir une responsabilité clairement définie.

Cette étape valide le principe fondamental de LabPilot : le modèle peut décider d'utiliser un outil, l'agent peut l'exécuter, le résultat peut être réinjecté dans le raisonnement du modèle et l'historique de la conversation peut être conservé de manière persistante.

Les tests montrent également que le modèle peut interpréter les résultats des outils et formuler une réponse contextualisée. Cette interprétation reste toutefois dépendante du raisonnement du modèle et peut être imparfaite.

### Prochaine étape

Le mécanisme d'outils gère désormais les appels successifs, les erreurs d'exécution, la protection contre les boucles incontrôlées et l'interprétation des résultats.

L'historique des conversations peut désormais être persisté localement avec SQLite.

La prochaine évolution consiste à poursuivre la consolidation de l'architecture TypeScript puis à intégrer progressivement de véritables outils de supervision du Homelab.

---

## 📄 Licence

La licence du projet sera définie ultérieurement.

---

## 🤝 Contribution

Les règles de contribution seront définies lorsque l'architecture initiale du projet sera stabilisée.

---

## 💬 Conversations persistantes dans le terminal

LabPilot dispose d'un service de gestion des conversations permettant de conserver l'historique des échanges et de reprendre une conversation ultérieurement.

### Démarrer LabPilot

Depuis la racine du projet, exécuter :

```bash
npm run chat
```

Cette commande compile le projet TypeScript puis lance le terminal interactif. Une nouvelle conversation est créée au démarrage et son identifiant est affiché.

### Commandes disponibles

| Commande | Description |
|---|---|
| `/help` | Afficher l'aide |
| `/new` | Créer une nouvelle conversation |
| `/resume <id>` | Reprendre une conversation existante |
| `/quit` | Quitter le terminal |

Tout texte qui n'est pas une commande est transmis à l'agent. LabPilot affiche ensuite sa réponse finale.

### Persistance et reprise

Les conversations sont enregistrées dans une base SQLite locale :

```text
data/labpilot.db
```

L'historique conserve les messages utilisateur, les réponses de l'assistant, les appels d'outils et leurs résultats.

Une conversation peut être reprise après la fermeture puis le redémarrage de LabPilot, à condition de disposer de son identifiant. Les nouvelles conversations possèdent un historique indépendant.

Le répertoire `data/` contient les données locales et ne doit pas être versionné dans Git.

### Vérifications

Vérifier les types TypeScript :

```bash
npm run typecheck
```

Compiler le projet :

```bash
npm run build
```

Exécuter les tests TypeScript :

```bash
npm run test:ts
```

Exécuter les tests d'intégration avec Ollama :

```bash
npm run test:integration
```

Les tests d'intégration nécessitent un serveur Ollama accessible et un modèle compatible avec la configuration du projet.
