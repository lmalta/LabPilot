# LabPilot

> Agent IA local pour la supervision, l'analyse et, à terme, l'automatisation contrôlée d'une infrastructure Homelab.

**État du projet :** développement actif — agent en lecture seule.

---

## Sommaire

- [Vision et principes](#-vision-et-principes)
- [Architecture](#-architecture)
- [Fonctionnement de l'agent](#-fonctionnement-de-lagent)
- [Prérequis](#-prérequis)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Intégration Proxmox](#-intégration-proxmox)
- [Sécurité Proxmox : rôle, ACL et token API](#-sécurité-proxmox--rôle-acl-et-token-api)
- [Certificat TLS de Proxmox](#-certificat-tls-de-proxmox)
- [Lancement et utilisation](#-lancement-et-utilisation)
- [Tests et validation](#-tests-et-validation)
- [Dépannage](#-dépannage)
- [Sécurité générale](#-sécurité-générale)
- [Feuille de route](#-feuille-de-route)
- [Veille, météo, CVE et pentest](#-veille-météo-cve-et-pentest)
- [Structure du projet](#-structure-du-projet)

---

## 🎯 Vision et principes

LabPilot est un agent IA local conçu pour observer une infrastructure Homelab, collecter des informations, les analyser et les présenter en langage naturel.

L'évolution prévue est progressive :

1. Observer l'infrastructure.
2. Comprendre les informations collectées.
3. Détecter des incohérences et des problèmes.
4. Expliquer les résultats.
5. Proposer des actions.
6. Demander une confirmation avant toute action autorisée.
7. Exécuter l'action et vérifier son résultat.

La priorité actuelle est la **supervision en lecture seule**.

Les principes fondamentaux sont :

- exécution locale des modèles IA ;
- séparation entre orchestration et exécution des outils ;
- composants indépendants et testables ;
- permissions minimales ;
- secrets exclus du dépôt Git ;
- documentation des opérations nécessaires à la reproduction de l'installation ;
- aucune action d'administration sans contrôle explicite.

---

## 🏗️ Architecture

LabPilot adopte progressivement une architecture mixte TypeScript / Python.

```text
Utilisateur
    |
    v
Orchestrateur TypeScript
    |
    +------ OllamaClient ------> API Ollama ------> Modèle local
    |
    +------ Catalogue des outils
                  |
                  v
             executerOutil()
                  |
                  v
               PontPython
                  |
                  v
          Processus Python persistant
                  |
                  v
             Outils Python
                  |
          +-------+--------+
          |       |        |
          v       v        v
       Système   GPU   Homelab
                         |
                    +----+----+
                    |         |
                    v         v
                Home      Proxmox
               Assistant
```

### TypeScript et Node.js

TypeScript prend progressivement en charge :

- l'orchestration de l'agent ;
- les échanges avec Ollama ;
- la déclaration des outils accessibles au modèle ;
- la boucle d'appels d'outils ;
- l'historique des conversations ;
- la persistance SQLite ;
- les communications futures avec une interface web et des API.

### Python

Python reste utilisé pour :

- l'exécution des outils ;
- la supervision du système et du GPU ;
- les interactions avec les API externes ;
- les futurs traitements documentaires et services IA ;
- les traitements nécessitant l'écosystème Python.

### Pont TypeScript → Python

Le pont Python est un processus persistant utilisant un protocole JSON Lines :

- une requête JSON par ligne ;
- une réponse JSON par ligne ;
- transmission des arguments ;
- retour du résultat ou d'une erreur ;
- gestion contrôlée du cycle de vie du processus.

Les exécutions sont actuellement séquentielles. L'orchestrateur applique une limite de 10 itérations afin d'éviter les boucles incontrôlées d'appels d'outils.

---

## 🧠 Fonctionnement de l'agent

L'orchestrateur transmet à Ollama l'historique de la conversation et les définitions des outils disponibles.

Lorsque le modèle demande un outil :

1. TypeScript vérifie que l'outil est déclaré.
2. La demande et ses arguments sont transmis au pont Python.
3. Python exécute l'outil.
4. Le résultat est retourné à TypeScript.
5. Le résultat est ajouté à l'historique.
6. L'orchestrateur sollicite à nouveau le modèle.
7. Le cycle continue jusqu'à une réponse finale ou à l'atteinte de la limite d'itérations.

Le modèle ne doit pas être considéré comme une source de vérité pour les données techniques. Lorsqu'un outil fournit des compteurs ou des résultats structurés, ceux-ci doivent être privilégiés et leur cohérence vérifiée.

Les erreurs fonctionnelles des outils peuvent être transmises au modèle. Les erreurs techniques du pont doivent être traitées séparément.

### Historique des conversations

L'historique est géré par `HistoriqueMessages` et les composants de dépôt de conversations.

La persistance actuelle repose sur SQLite :

```text
data/labpilot.db
```

Les messages utilisateur, réponses de l'assistant, appels d'outils et résultats peuvent être conservés afin de reprendre une conversation.

Le répertoire `data/` contient des données locales et ne doit pas être versionné.

---

## 🧰 Outils disponibles

Le catalogue évolue au fil des intégrations. Il comprend notamment :

- `heure_actuelle` : obtenir l'heure courante ;
- `heure_dans` : calculer une heure future ;
- `etat_systeme` : consulter les informations générales du système ;
- `etat_gpu` : consulter l'état du GPU ;
- `etat_ollama` : consulter le serveur Ollama et les modèles ;
- `etat_home_assistant` : consulter des informations de Home Assistant ;
- `etat_proxmox` : consulter les nœuds et machines du cluster Proxmox ;
- `inventaire_os_proxmox` : collecter les informations OS des VM QEMU en fonctionnement via le QEMU Guest Agent ;
- `rechercher_cve` : rechercher des CVE candidates dans la base publique NVD à partir d'un produit et d'une version. Les résultats sont indicatifs et ne confirment pas l'applicabilité d'une vulnérabilité ;
- `audit_cve_proxmox` : inventorier les OS des VM QEMU en fonctionnement et rechercher des CVE candidates pour chaque machine dont l'OS et la version sont identifiés.

Les outils Proxmox sont conçus pour fonctionner en lecture seule.

---

## 🖥️ Prérequis

L'environnement actuel utilise :

- Linux / Ubuntu ;
- Python et un environnement virtuel ;
- Node.js et npm ;
- TypeScript ;
- Ollama accessible par API ;
- Git ;
- pytest pour les tests Python.

Les versions exactes doivent être relevées sur la machine lors d'une reconstruction de l'environnement.

---

## 📦 Installation

Depuis la racine du dépôt :

```bash
cd ~/LabPilot
```

### Environnement Python

Si l'environnement virtuel existe déjà :

```bash
source .venv/bin/activate
```

Pour installer les dépendances Python dans un environnement neuf :

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Dépendances Node.js

```bash
npm ci
```

### Compilation

```bash
npm run typecheck
npm run build
```

---

## ⚙️ Configuration

LabPilot utilise un fichier `.env` local pour les paramètres propres à l'installation.

Le fichier `.env.example` fournit un modèle sans secrets réels.

Créer le fichier local si nécessaire :

```bash
cp .env.example .env
nano .env
```

Ne pas écraser un `.env` existant contenant une configuration valide.

### Ollama

La configuration doit notamment définir l'adresse de l'API Ollama et le modèle utilisé, conformément aux variables attendues par le code.

Exemple d'adresse :

```text
OLLAMA_URL=http://<ADRESSE_OLLAMA>:11434
```

### Home Assistant

L'intégration Home Assistant utilise une URL et un jeton d'accès local. Les noms exacts des variables doivent correspondre à ceux de `.env.example` et du module de configuration.

### Proxmox

Les variables attendues sont :

```dotenv
PROXMOX_URL=https://<NOM_DNS_OU_IP_PROXMOX>:8006
PROXMOX_TOKEN_ID=<UTILISATEUR>@pve!<NOM_TOKEN>
PROXMOX_TOKEN_SECRET=<SECRET_DU_TOKEN>
```

Exemple de format d'identifiant de token :

```text
labpilot@pve!labpilot-readonly
```

Cet exemple est un identifiant de démonstration, pas un secret.

**Ne jamais mettre le véritable secret dans le README, dans `.env.example`, dans une commande enregistrée dans l'historique du shell ou dans Git.**

---

## 🖥️ Intégration Proxmox

### Objectif

L'outil `etat_proxmox` interroge l'API REST de Proxmox VE en lecture seule.

Il récupère les ressources du cluster, notamment :

- les nœuds ;
- les machines virtuelles QEMU ;
- les conteneurs LXC ;
- les états des machines ;
- les compteurs globaux par type et par état.

Le point d'accès utilisé est :

```text
GET /api2/json/cluster/resources
```

Le port HTTPS habituel de l'interface et de l'API Proxmox est `8006`.

### Données et états

Les types de machines sont distingués :

- `VM` : machine virtuelle QEMU ;
- `conteneur` : conteneur LXC.

Les états possibles comprennent :

- `running` : en cours d'exécution ;
- `stopped` : arrêté ;
- `unknown` : état non déterminable par les informations disponibles.

Un nœud hors ligne peut empêcher la récupération de l'état actuel de ses machines. Dans ce cas, `unknown` ne doit pas être assimilé à `stopped`.

Les compteurs `machines_par_type`, `machines_par_etat` et `machines_par_type_et_etat` doivent provenir des données calculées par l'outil. Le modèle ne doit pas inventer de noms ni reconstruire des compteurs contradictoires.

### Inventaire des systèmes d'exploitation des VM

L'outil `inventaire_os_proxmox` complète `etat_proxmox` en collectant les informations du système d'exploitation des machines virtuelles QEMU en fonctionnement.

Il utilise l'API Proxmox VE et le **QEMU Guest Agent** de chaque VM. Les informations collectées comprennent :

- le nom de la VM, son identifiant et son nœud Proxmox ;
- le nom du système d'exploitation ;
- sa version et son identifiant de version, lorsqu'ils sont disponibles ;
- la version du noyau, lorsqu'elle est disponible ;
- l'état de la collecte.

L'outil fonctionne en lecture seule. Si l'agent invité ne répond pas, si les informations sont invalides ou si l'OS ne peut pas être identifié, le résultat indique un état de collecte approprié.

**Limites actuelles :**

- seules les VM QEMU en fonctionnement sont prises en compte ;
- les conteneurs LXC ne sont pas couverts par cet outil ;
- la collecte des informations OS ne constitue pas, à elle seule, une détection de vulnérabilités ;
- un premier audit recherche des CVE candidates dans NVD pour les OS et versions identifiés ;
- la vérification de l'applicabilité à partir des CPE, des versions affectées et des avis des fournisseurs reste à développer.

### Configuration de l'accès

L'intégration nécessite :

1. un utilisateur Proxmox dédié ou explicitement choisi ;
2. un rôle en lecture seule ;
3. une ACL affectée au périmètre approprié ;
4. un token API ;
5. le secret du token dans le fichier `.env` local ;
6. le certificat CA permettant de vérifier le serveur HTTPS.

La création du token et des droits est détaillée dans la section suivante.

---

## 🔐 Sécurité Proxmox : rôle, ACL et token API

Cette section documente les principes à respecter pour configurer l'accès de LabPilot à Proxmox.

Les libellés exacts de l'interface peuvent varier selon la version de Proxmox VE.

### 1. Créer ou choisir un utilisateur dédié

Dans l'interface Proxmox, ouvrir :

**Datacenter → Permissions → Users**

Utiliser de préférence un compte technique dédié à LabPilot, plutôt qu'un compte administrateur personnel.

Exemple d'identifiant :

```text
labpilot@pve
```

Cet utilisateur ne doit disposer d'aucun privilège d'administration inutile.

### 2. Comprendre le rôle

Proxmox fournit notamment le rôle prédéfini `PVEAuditor`, destiné à l'audit et à la consultation.

Ce rôle est adapté à un accès de supervision en lecture seule lorsque ses privilèges couvrent les opérations nécessaires à l'outil.

Il ne faut pas lui ajouter de privilèges d'écriture simplement pour résoudre une erreur d'accès.

Si une permission manque, identifier précisément l'API concernée et vérifier le périmètre de l'ACL avant toute modification.

### 3. Comprendre les ACL

Une ACL associe un utilisateur ou un token, un rôle et un chemin de ressources.

Dans l'interface, ouvrir :

**Datacenter → Permissions → Permissions**

Les périmètres possibles comprennent notamment :

- `/` : racine du cluster ;
- `/nodes` : ressources associées aux nœuds ;
- un chemin plus restreint, si les ressources et privilèges nécessaires le permettent.

Le choix du chemin doit correspondre au besoin réel de LabPilot.

Pour une supervision globale du cluster, les droits doivent couvrir les ressources nécessaires à la consultation des nœuds et des machines. Une ACL limitée à un seul nœud ne permet pas nécessairement de superviser tout le cluster.

Ne pas créer plusieurs ACL plus larges que nécessaire pour contourner une erreur dont la cause n'a pas été identifiée.

### 4. Créer un token API

Dans l'interface Proxmox, ouvrir :

**Datacenter → Permissions → API Tokens**

Créer un token pour l'utilisateur technique.

Exemple de nom :

```text
labpilot-readonly
```

L'identifiant complet prend généralement la forme :

```text
labpilot@pve!labpilot-readonly
```

Proxmox affiche le secret lors de la création du token. Il doit être copié immédiatement et stocké de manière sécurisée.

Il ne faut pas compter sur la possibilité de retrouver ultérieurement le secret en clair dans l'interface.

### 5. Comprendre la séparation des privilèges

Lors de la création du token, Proxmox propose une option de séparation des privilèges (*Privilege Separation*).

Son comportement est important :

- lorsque la séparation est activée, les permissions effectives du token sont limitées par celles de son utilisateur et par les droits accordés au token ;
- lorsque la séparation est désactivée, le token utilise les permissions de son utilisateur et il n'est pas possible de considérer le token comme une identité indépendante dotée de droits plus restreints.

Pour un token de supervision, il faut documenter explicitement le mode retenu et vérifier les ACL correspondantes.

**Ne pas supposer qu'un token est en lecture seule uniquement parce que son nom contient `readonly`.** Le nom ne constitue pas un contrôle de sécurité.

### 6. Vérifier les permissions effectives

Avant d'utiliser le token, vérifier :

- l'utilisateur auquel il appartient ;
- le rôle affecté ;
- le chemin de l'ACL ;
- le mode de séparation des privilèges ;
- les permissions effectives de l'utilisateur et du token ;
- l'absence de droits d'écriture inutiles.

Le but est de permettre les requêtes de consultation nécessaires à LabPilot sans autoriser les modifications des machines, du stockage ou de la configuration du cluster.

### 7. Stocker le secret localement

Dans le fichier `.env` local :

```dotenv
PROXMOX_URL=https://<NOM_DNS_OU_IP_PROXMOX>:8006
PROXMOX_TOKEN_ID=labpilot@pve!labpilot-readonly
PROXMOX_TOKEN_SECRET=<SECRET_REEL_DU_TOKEN>
```

Le secret ne doit être partagé ni dans les messages de diagnostic ni dans les captures d'écran.

Vérifier que `.env` est ignoré par Git :

```bash
git check-ignore .env
```

Si cette commande ne confirme pas que le fichier est ignoré, corriger `.gitignore` avant de poursuivre.

Ne pas ajouter le fichier `.env` à l'index Git.

---

## 🔒 Certificat TLS de Proxmox

LabPilot vérifie le certificat HTTPS du serveur Proxmox au moyen d'un certificat CA local.

Le fichier attendu par l'outil est :

```text
certs/proxmox-root-ca.pem
```

Le chemin est défini dans `labpilot/tools.py`.

Le certificat CA doit être obtenu depuis une source fiable, correspondant à l'autorité qui a signé le certificat du serveur Proxmox.

### Pourquoi installer le certificat CA ?

Une connexion HTTPS ne doit pas être considérée comme sûre simplement parce qu'elle utilise le port `8006`.

La vérification TLS permet de vérifier la chaîne de confiance du certificat du serveur et de détecter notamment un certificat non reconnu ou une interception.

Le client Python crée son contexte TLS à partir du fichier CA :

```python
ssl.create_default_context(
    cafile=PROXMOX_CA_FILE
)
```

Le certificat du serveur doit également correspondre au nom utilisé dans `PROXMOX_URL`.

Si l'URL utilise un nom DNS, ce nom doit être présent dans les noms couverts par le certificat. Si l'URL utilise une adresse IP, le certificat doit être valide pour cette adresse IP.

### Installer le certificat

Depuis la racine du projet :

```bash
mkdir -p certs
```

Copier le certificat CA obtenu de manière fiable vers :

```text
certs/proxmox-root-ca.pem
```

Le certificat public CA peut être versionné uniquement si cela est volontaire, sûr et adapté au projet. Pour l'installation actuelle, il reste local et est exclu du dépôt.

Ne jamais remplacer la vérification TLS par un mode qui accepte tous les certificats.

### Vérifier le fichier

```bash
test -f certs/proxmox-root-ca.pem \
  && echo "Certificat CA présent" \
  || echo "Certificat CA manquant"
```

Si le fichier est absent ou invalide, l'outil doit signaler une erreur plutôt que désactiver la validation du certificat.

---

## 🚀 Lancement et utilisation

Depuis la racine du dépôt, avec l'environnement Python activé :

```bash
npm run chat
```

Cette commande compile le projet TypeScript et lance le terminal interactif.

### Commandes du terminal

| Commande | Description |
|---|---|
| `/help` | Afficher l'aide |
| `/new` | Créer une nouvelle conversation |
| `/resume <id>` | Reprendre une conversation |
| `/quit` | Quitter le terminal |

Pour tester Proxmox, poser une question explicite, par exemple :

```text
Donne-moi l'état des nœuds et des machines du cluster Proxmox.
```

Pour vérifier les compteurs :

```text
Pour chaque type de machine, donne les nombres running,
stopped et unknown directement depuis le compteur
machines_par_type_et_etat fourni par l'outil.
Vérifie la cohérence du total.
```

Les réponses du modèle doivent être contrôlées par rapport aux résultats structurés de l'outil.

---

## 🧪 Tests et validation

### Tests Python

Activer l'environnement virtuel si nécessaire :

```bash
source .venv/bin/activate
```

Exécuter les tests :

```bash
python -m pytest -q
```

Vérifier la syntaxe Python :

```bash
python -m py_compile labpilot/tools.py
```

### Tests TypeScript

Vérifier les types :

```bash
npm run typecheck
```

Compiler :

```bash
npm run build
```

Exécuter les tests TypeScript :

```bash
npm run test:ts
```

### Vérifier les modifications Git

```bash
git diff --check
git status --short
```

Ces commandes permettent de repérer les erreurs de formatage et de vérifier quels fichiers ont été modifiés.

### Validation Proxmox

La validation doit confirmer :

- la résolution du nom du serveur ;
- l'accessibilité HTTPS sur le port `8006` ;
- la validité du certificat TLS ;
- la présence des trois variables `PROXMOX_*` nécessaires ;
- la présence du certificat CA ;
- l'authentification du token ;
- l'accès en lecture aux ressources attendues ;
- le traitement des erreurs de connexion et de permission ;
- la cohérence des compteurs retournés.

Un test réalisé contre un cluster réel doit être complété par des tests unitaires avec des réponses simulées.

---

## 🛠️ Dépannage

### Variables Proxmox manquantes

Vérifier que `.env` contient les trois variables :

```text
PROXMOX_URL
PROXMOX_TOKEN_ID
PROXMOX_TOKEN_SECRET
```

Ne pas afficher la valeur du secret pour vérifier sa présence.

### Certificat CA manquant

Vérifier le fichier :

```bash
test -f certs/proxmox-root-ca.pem
```

Si le fichier manque, le restaurer depuis une source fiable.

### Erreur TLS

Vérifier :

- que le certificat CA correspond à celui utilisé par Proxmox ;
- que le certificat serveur n'est pas expiré ;
- que le nom DNS ou l'adresse IP de l'URL correspond au certificat ;
- que l'horloge du système est correcte.

Ne pas désactiver la validation TLS pour contourner l'erreur.

### Erreur d'authentification ou de permissions

Vérifier :

- l'identifiant complet du token ;
- la valeur du secret dans le fichier local ;
- le fait que le token existe et n'a pas été révoqué ;
- l'utilisateur auquel le token appartient ;
- le mode de séparation des privilèges ;
- le rôle et le chemin de l'ACL ;
- les permissions effectives sur les ressources interrogées.

Ne pas résoudre une erreur de permission en attribuant automatiquement des droits d'administrateur.

### Nœud hors ligne et état `unknown`

Un nœud indisponible peut empêcher de déterminer l'état actuel de ses machines. `unknown` indique une information non disponible ou non déterminable ; cela ne signifie pas que la machine est arrêtée.

### Erreur Ollama

Vérifier que le service Ollama est actif, que l'URL est correcte et que le modèle demandé est disponible.

---

## 🔐 Sécurité générale

Le dépôt doit pouvoir être rendu public sans nettoyage préalable.

Ne jamais versionner :

- les secrets et mots de passe ;
- les tokens API ;
- les clés privées ;
- les fichiers `.env` locaux ;
- les bases de conversations ;
- les données personnelles ;
- les configurations internes sensibles ;
- les exports de diagnostic contenant des secrets.

Les adresses, noms DNS et chemins spécifiques à une installation doivent être remplacés par des exemples dans la documentation publique.

Les fichiers de configuration d'exemple ne doivent contenir que des valeurs fictives ou des placeholders.

La sécurité doit reposer sur des contrôles effectifs :

- permissions minimales ;
- secrets hors du dépôt ;
- validation TLS ;
- traitement explicite des erreurs ;
- journalisation sans secrets ;
- confirmation humaine avant les futures actions sensibles.

> Tout ce qui est commité dans LabPilot doit pouvoir être rendu public sans nettoyage préalable.

---

## 🗺️ Feuille de route

Les cases cochées correspondent aux fonctionnalités déjà implémentées selon le code et la documentation disponibles. Une fonctionnalité partielle ou dont la validation complète reste à faire n'est pas déclarée terminée.

### Phase 1 — Fondations

- [x] Créer le dépôt GitHub.
- [x] Définir le nom et le périmètre initial du projet.
- [x] Définir les principes de sécurité.
- [x] Créer la structure initiale.
- [x] Mettre en place la configuration.
- [x] Communiquer avec le modèle IA local.
- [x] Séparer l'agent de la communication avec Ollama.
- [x] Mettre en place un historique de conversation.

### Phase 2 — Premier agent en lecture seule

- [x] Mettre en place la boucle de fonctionnement de l'agent.
- [x] Déclarer les outils et transmettre leurs arguments.
- [x] Exécuter les outils et renvoyer leurs résultats au modèle.
- [x] Générer une réponse finale à partir du résultat d'un outil.
- [x] Tester le choix automatique des outils.
- [x] Utiliser l'historique des conversations avec les outils.
- [x] Créer l'outil d'état du système.
- [x] Créer l'outil d'état du GPU.
- [x] Créer l'outil d'état d'Ollama.
- [x] Tester le raisonnement à partir des résultats.
- [x] Gérer plusieurs appels d'outils successifs.
- [x] Gérer les erreurs d'exécution.
- [x] Limiter les boucles d'appels d'outils.

### Phase 3 — Intégration du Homelab

- [x] Intégrer Home Assistant en lecture seule.
- [x] Récupérer les informations de version de Home Assistant.
- [x] Compter les entités et les répartir par domaine.
- [x] Ajouter l'outil Proxmox en lecture seule.
- [x] Calculer les compteurs de machines par type et par état.
- [x] Déclarer l'outil Proxmox dans le catalogue TypeScript.
- [x] Ajouter l'inventaire des systèmes d'exploitation des VM QEMU via le QEMU Guest Agent.
- [x] Déclarer l'outil d'inventaire OS dans les catalogues Python et TypeScript.
- [ ] Finaliser et valider la documentation Proxmox.
- [ ] Ajouter des tests explicites pour les erreurs Proxmox : connexion, authentification, permissions et réponses invalides.
- [ ] Ajouter des outils réseau.
- [ ] Ajouter des outils de stockage.
- [ ] Ajouter des outils de supervision.
- [ ] Améliorer les rapports d'état.

### Phase 4 — Automatisation contrôlée

- [ ] Définir les actions autorisées.
- [ ] Mettre en place les demandes de confirmation.
- [ ] Journaliser les actions sans exposer de secrets.
- [ ] Définir les permissions par action.
- [ ] Tester les erreurs et les situations de récupération.
- [ ] Empêcher les actions dangereuses non confirmées.

### Phase 5 — Architecture de production

- [ ] Séparer LabPilot du serveur de modèle IA.
- [ ] Déployer LabPilot comme service indépendant.
- [ ] Conteneuriser l'application.
- [ ] Étudier un déploiement K3s.
- [ ] Améliorer la supervision.
- [ ] Renforcer la sécurité.

---

### Phase 6 — Veille et informations externes

- [ ] Définir une architecture modulaire de collecte des informations.
- [ ] Intégrer des flux RSS d’actualités.
- [ ] Intégrer une source météo adaptée.
- [ ] Collecter les alertes et actualités météorologiques pertinentes.
- [ ] Filtrer, dédupliquer et classer les informations.
- [ ] Produire des synthèses à partir des informations collectées.
- [ ] Permettre la sélection des sources et des sujets suivis.

### Phase 7 — Veille de sécurité du Homelab

**État : première brique d'audit CVE implémentée ; validation de l'applicabilité et automatisation encore à développer.**

- [ ] Inventorier les composants du Homelab et leurs versions.
  - [x] Récupérer les informations OS des VM QEMU en fonctionnement via le QEMU Guest Agent.
  - [ ] Compléter et valider l'inventaire des versions des logiciels et services installés.
- [ ] Collecter les CVE et avis de sécurité depuis des sources fiables.
  - [x] Interroger l'API publique NVD pour rechercher des CVE candidates par produit/version.
  - [x] Intégrer le Debian Security Tracker pour les VM Debian prises en charge (Debian 11, 12 et 13), avec rapprochement sur l'inventaire réel des paquets installés.
  - [ ] Ajouter et valider d'autres sources spécialisées et avis fournisseurs pour les systèmes présents dans le Homelab.
- [ ] Identifier les vulnérabilités potentiellement applicables.
  - [x] Distinguer les résultats candidats des vulnérabilités confirmées dans le contrat de résultat.
  - [ ] Vérifier les CPE, versions affectées et preuves avant de conclure sur l'applicabilité.
- [ ] Vérifier les versions affectées et les correctifs disponibles.
  - [ ] Intégrer les règles et données propres aux distributions et produits concernés.
  - [ ] Vérifier les versions corrigées et les avis de sécurité des fournisseurs.
- [ ] Générer des rapports de vulnérabilités priorisés.
  - [ ] Définir la priorisation selon la sévérité, l'exposition et le contexte Homelab.
  - [ ] Produire un rapport exploitable avec les preuves, les incertitudes et les recommandations.
- [ ] Automatiser les contrôles périodiques et les rapports.
  - [ ] Définir une planification, la gestion des erreurs et l'historique des audits.
- [ ] Préparer des recommandations de remédiation sans appliquer automatiquement les actions risquées.

**Travaux techniques déjà réalisés :**
- [x] Normaliser la structure des résultats CVE et conserver les champs historiques nécessaires à la compatibilité.
- [x] Valider la structure du contrat et les statuts autorisés.
- [x] Normaliser les erreurs et réponses invalides afin qu'un échec sur une machine n'interrompe pas tout l'audit.
- [x] Détecter séparément TrueNAS et Home Assistant OS pour éviter une recherche générique trompeuse sur un OS sous-jacent.
- [ ] Vérifier les preuves associées aux statuts de confirmation : la validation structurelle actuelle ne garantit pas à elle seule la justesse d'une conclusion.
- [x] Ajouter un connecteur Debian fondé sur le Debian Security Tracker et l'inventaire des paquets via QEMU Guest Agent.
- [ ] Ajouter ou intégrer des connecteurs adaptés à Nextcloud, TrueNAS, Home Assistant OS et, plus tard, k3s.
- [x] Exécuter la suite de tests Python après l'intégration du connecteur Debian (129 tests réussis lors de la dernière validation locale).

### Phase 8 — Audit de sécurité et pentest automatisé

- [ ] Définir le périmètre autorisé et les règles d’exécution.
- [ ] Réaliser des contrôles de configuration et de sécurité.
- [ ] Automatiser la détection et la validation non destructive des vulnérabilités.
- [ ] Ajouter des tests ciblés sur les services explicitement autorisés.
- [ ] Encadrer les tests intrusifs par des limites et des confirmations.
- [ ] Produire des rapports avec preuves, risques et mesures correctives.
- [ ] Vérifier les corrections après remédiation.
- [ ] Étudier des scénarios d’exploitation contrôlée dans un environnement isolé.
- [ ] Valider le processus complet avant toute extension à d’autres systèmes.

## 📁 Structure du projet

La structure évolue avec les fonctionnalités. Les principaux composants comprennent :

```text
LabPilot/
├── src/
│   ├── index.ts
│   ├── labpilot.ts
│   ├── types.ts
│   ├── orchestrateur.ts
│   ├── ollama-client.ts
│   ├── pont-python.ts
│   ├── historique.ts
│   ├── depot-conversations.ts
│   └── depot-conversations-sqlite.ts
├── labpilot/
│   ├── configuration.py
│   ├── tools.py
│   └── bridge.py
├── tests/
├── tests-ts/
├── certs/
│   └── proxmox-root-ca.pem
├── data/
│   └── labpilot.db
├── .env.example
├── requirements.txt
├── package.json
├── package-lock.json
└── README.md
```

Cette représentation est indicative : certains fichiers peuvent évoluer ou être ajoutés au cours du développement.

Les répertoires `data/`, `.venv/`, `node_modules/`, les fichiers `.env` locaux et les certificats propres à l'installation doivent rester hors du dépôt lorsque leur contenu est spécifique à l'environnement.

---

## 📄 Licence et contribution

LabPilot est distribué sous licence [MIT](LICENSE).

Vous êtes libre d'utiliser, de copier, de modifier et de distribuer ce logiciel, y compris à des fins commerciales, sous réserve de conserver les mentions de copyright et de licence.

Consultez le fichier [LICENSE](LICENSE) pour connaître les conditions complètes.

---

Les contributions seront très prochainement ouvertes.

## 🌦️ Veille, météo, CVE et pentest

Les flux RSS, la veille météo et le pentest automatisé restent des objectifs de la feuille de route. La recherche de CVE dispose désormais d'un premier outil dédié utilisant l'API publique NVD.

### Recherche de CVE

L'outil `rechercher_cve` interroge l'API NVD à partir d'un nom de produit et d'une version.

Paramètres :
- `produit` : nom du logiciel ou du produit recherché ;
- `version` : version à examiner ;
- `limite` : nombre maximal de résultats, de 1 à 20 (20 par défaut).

Les résultats peuvent inclure l'identifiant CVE, la description en anglais, le score CVSS lorsqu'il est disponible, les dates de publication et de modification, ainsi que les références associées. L'adaptateur de l'audit expose également une représentation normalisée commune aux futurs connecteurs, tout en conservant les champs historiques utilisés par l'outil.

**Limites importantes :**
- une recherche par mots-clés ne prouve pas qu'une CVE affecte effectivement le produit installé ;
- l'applicabilité doit être vérifiée à partir des versions affectées, des CPE et des avis de sécurité du fournisseur ;
- l'absence de résultat ne garantit pas l'absence de vulnérabilité ;
- la disponibilité de l'API et la qualité des informations retournées dépendent de la source NVD.

Cet outil est destiné à la veille et à l'analyse en lecture seule. Il ne corrige pas les vulnérabilités et ne lance aucun test intrusif.

La démarche de sécurité évoluera progressivement : inventaire des systèmes, recherche de vulnérabilités candidates, vérification de leur applicabilité, puis contrôles non destructifs sur les systèmes autorisés.

### Audit CVE des VM Proxmox

L'outil `audit_cve_proxmox` automatise les premières étapes de la recherche de vulnérabilités sur les machines virtuelles QEMU en fonctionnement. Il privilégie un connecteur de sécurité spécialisé lorsqu'il est enregistré pour le système détecté ; pour Debian, il utilise le Debian Security Tracker et l'inventaire réel des paquets.

**Fonctionnement :**
1. Collecte les informations du système d'exploitation via `inventaire_os_proxmox` et le QEMU Guest Agent.
2. Ignore les machines dont l'OS ou la version ne sont pas identifiés.
3. Utilise le connecteur de sécurité enregistré lorsqu'il existe. Pour Debian 11, 12 et 13, collecte les paquets installés via le QEMU Guest Agent puis rapproche leurs paquets sources et versions du Debian Security Tracker. À défaut de connecteur spécialisé, utilise la recherche NVD par produit/version lorsque celle-ci est autorisée.
4. Conserve les résultats normalisés détaillés, limite séparément la liste résumée affichée et traite les erreurs individuellement afin qu'un échec de recherche ne bloque pas l'audit des autres machines.

**Paramètre :**
- `limite_par_machine` : nombre maximal de CVE candidates recherchées par machine, de 1 à 20 (20 par défaut).

**États possibles de l'audit :**
- `terminee` : recherche effectuée ;
- `ignoree_os_non_identifie` : système d'exploitation non identifié ou collecte incomplète ;
- `ignoree_version_inconnue` : version du système inconnue ;
- `erreur_recherche_cve` : recherche NVD impossible ou réponse invalide ;
- `connecteur_securite_termine` : audit terminé par un connecteur de sécurité spécialisé ;
- `erreur_connecteur_securite` : connecteur spécialisé indisponible ou en erreur.

**Résultat CVE normalisé :**

Pour préparer l'intégration de sources spécialisées, les réponses de recherche peuvent être converties vers un contrat commun contenant `produit`, `version_detectee`, `source`, `disponible`, `erreur` et `resultats`. Chaque avis normalisé comprend `identifiant`, `versions_affectees`, `version_corrigee`, `statut`, `preuve` et `date_verification`.

Pour Debian, le connecteur conserve notamment le paquet source, la version source installée, les paquets binaires associés et la date de vérification. Les résultats sont dédupliqués par avis CVE et paquet source/version afin d'éviter les répétitions dues à plusieurs paquets binaires issus d'une même source. La liste résumée `cve` est limitée par `limite_par_machine` (20 par défaut), tandis que `resultat_cve_normalise` conserve les résultats détaillés.

Les statuts actuellement autorisés sont :
- `candidate` : résultat trouvé par la recherche, applicabilité non confirmée ;
- `potentiellement_affectee` : hypothèse à examiner, qui nécessite des éléments probants ;
- `affectee_confirmee` : vulnérabilité confirmée par des preuves adaptées ;
- `non_affectee` : non-applicabilité établie par des preuves ;
- `correctif_disponible` : correctif identifié ;
- `verification_incomplete` : informations insuffisantes pour conclure.

À ce stade, la recherche NVD par mots-clés classe ses résultats comme `candidate`. Le contrat valide la structure et les valeurs de statut autorisées, mais ne vérifie pas encore que les preuves fournies justifient chaque statut. Les statuts de confirmation ne doivent donc pas être attribués automatiquement sur la seule base d'une correspondance de nom ou de version.

**Systèmes spécialisés :**
- TrueNAS est détecté séparément ; en l'absence de version produit fiable et de connecteur adapté, l'audit évite de traiter son noyau comme une version Debian générique.
- Home Assistant OS est détecté séparément et ignoré par la recherche NVD générique tant qu'une source spécialisée n'est pas intégrée.
- Les erreurs et réponses invalides d'une recherche sont normalisées sans interrompre l'audit des autres machines.

**Limites et sécurité :**
- L'audit porte sur les VM QEMU en fonctionnement ; il ne couvre pas les conteneurs LXC.
- La collecte de l'OS nécessite un QEMU Guest Agent opérationnel et accessible.
- Les résultats NVD sont des CVE candidates issues d'une recherche par mots-clés. Ils ne prouvent pas qu'une vulnérabilité affecte effectivement la machine.
- Les CPE, les versions affectées et les avis de sécurité des fournisseurs doivent être vérifiés avant toute conclusion.
- L'outil fonctionne en lecture seule : il ne corrige pas les vulnérabilités, ne modifie pas les machines et ne lance aucun test intrusif.

## 📌 État actuel du projet

LabPilot possède un premier socle fonctionnel comprenant :

- une orchestration TypeScript ;
- une communication avec Ollama ;
- un pont Python persistant ;
- un catalogue d'outils ;
- une boucle d'appels d'outils avec limite d'itérations ;
- un historique de conversation persistant avec SQLite ;
- des outils de supervision du système, du GPU et d'Ollama ;
- une intégration Home Assistant en lecture seule ;
- une intégration Proxmox en lecture seule ;
- un inventaire des systèmes d'exploitation des VM QEMU via le QEMU Guest Agent ;
- un audit CVE des VM QEMU avec recherche NVD générique et connecteur Debian basé sur l'inventaire des paquets et le Debian Security Tracker ;
- des tests unitaires Python et TypeScript.

L'interprétation du modèle peut rester imparfaite. Les informations techniques doivent être vérifiées à partir des résultats structurés des outils.

La prochaine étape consiste à renforcer les preuves nécessaires à la validation de l'applicabilité des CVE, puis à intégrer progressivement des sources de sécurité spécialisées pour les produits présents dans le Homelab.
