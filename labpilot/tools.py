import os
import platform
import subprocess
import math
import json
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from labpilot.configuration import (
    HOME_ASSISTANT_URL,
    HOME_ASSISTANT_TOKEN,
    PROXMOX_URL,
    PROXMOX_TOKEN_ID,
    PROXMOX_TOKEN_SECRET,
)

PROXMOX_CA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "certs",
    "proxmox-root-ca.pem",
)


def heure_actuelle() -> str:
    return datetime.now().astimezone().isoformat()


def heure_dans(minutes: int) -> str:
    return (datetime.now().astimezone() + timedelta(minutes=minutes)).isoformat()


def etat_systeme() -> dict:
    memoire = {}

    with open("/proc/meminfo") as fichier:
        for ligne in fichier:
            nom, valeur = ligne.split(":", 1)
            memoire[nom] = int(valeur.strip().split()[0])

    return {
        "nom_machine": platform.node(),
        "systeme": platform.system(),
        "version_noyau": platform.release(),
        "architecture": platform.machine(),
        "nombre_cpu": os.cpu_count(),
        "memoire_totale_mo": round(memoire["MemTotal"] / 1024),
        "memoire_disponible_mo": round(memoire["MemAvailable"] / 1024),
        "load_average_1min": os.getloadavg()[0],
        "load_average_5min": os.getloadavg()[1],
        "load_average_15min": os.getloadavg()[2],
    }


def etat_gpu() -> list[dict]:
    commande = [
        "nvidia-smi",
        "--query-gpu=index,name,memory.total,memory.used,memory.free,"
        "utilization.gpu,temperature.gpu,power.draw",
        "--format=csv,noheader,nounits",
    ]

    resultat = subprocess.run(
        commande,
        capture_output=True,
        text=True,
        check=True,
        timeout=5,
    )

    gpu = []

    for ligne in resultat.stdout.strip().splitlines():
        valeurs = [valeur.strip() for valeur in ligne.split(",")]

        gpu.append(
            {
                "index": int(valeurs[0]),
                "nom": valeurs[1],
                "memoire_totale_mo": int(valeurs[2]),
                "memoire_utilisee_mo": int(valeurs[3]),
                "memoire_disponible_mo": int(valeurs[4]),
                "utilisation_gpu_pourcent": int(valeurs[5]),
                "temperature_c": int(valeurs[6]),
                "consommation_w": float(valeurs[7]),
            }
        )

    return gpu


def etat_ollama() -> dict:
    base_url = "http://127.0.0.1:11434"

    with urllib.request.urlopen(
        f"{base_url}/api/version",
        timeout=5,
    ) as reponse:
        version = json.load(reponse)["version"]

    with urllib.request.urlopen(
        f"{base_url}/api/tags",
        timeout=5,
    ) as reponse:
        modeles = json.load(reponse)["models"]

    with urllib.request.urlopen(
        f"{base_url}/api/ps",
        timeout=5,
    ) as reponse:
        modeles_actifs = json.load(reponse)["models"]

    return {
        "disponible": True,
        "version": version,
        "modeles": [modele["name"] for modele in modeles],
        "modeles_actifs": [
            modele["name"] for modele in modeles_actifs
        ],
    }


def etat_home_assistant() -> dict:
    if not HOME_ASSISTANT_URL or not HOME_ASSISTANT_TOKEN:
        raise RuntimeError(
            "La configuration Home Assistant est absente."
        )

    base_url = HOME_ASSISTANT_URL.rstrip("/")

    def requete_api(chemin: str):
        requete = urllib.request.Request(
            f"{base_url}{chemin}",
            headers={
                "Authorization": f"Bearer {HOME_ASSISTANT_TOKEN}",
                "Content-Type": "application/json",
            },
        )

        with urllib.request.urlopen(requete, timeout=10) as reponse:
            return json.load(reponse)

    try:
        configuration = requete_api("/api/config")
        entites = requete_api("/api/states")
    except Exception as erreur:
        # Ne pas propager les détails HTTP susceptibles de contenir
        # des informations sensibles.
        raise RuntimeError(
            f"Impossible de consulter Home Assistant ({type(erreur).__name__})."
        ) from None

    domaines = {}

    for entite in entites:
        domaine = entite.get("entity_id", "inconnu").split(".", 1)[0]
        domaines[domaine] = domaines.get(domaine, 0) + 1

    return {
        "disponible": True,
        "version": configuration.get("version"),
        "nombre_entites": len(entites),
        "entites_par_domaine": dict(sorted(domaines.items())),
    }


def _nombre_proxmox_valide(valeur, nom_champ):
    """Vérifie qu'une valeur numérique fournie par Proxmox est valide."""
    if valeur is None:
        return

    if (
        isinstance(valeur, bool)
        or not isinstance(valeur, (int, float))
        or not math.isfinite(valeur)
        or valeur < 0
    ):
        raise RuntimeError(
            f"Réponse Proxmox invalide : valeur incorrecte pour {nom_champ}."
        )


def etat_proxmox() -> dict:
    """Retourne l'état des nœuds et des VM/conteneurs Proxmox en lecture seule."""
    if not all((PROXMOX_URL, PROXMOX_TOKEN_ID, PROXMOX_TOKEN_SECRET)):
        raise RuntimeError("La configuration Proxmox est absente.")

    if not os.path.isfile(PROXMOX_CA_FILE):
        raise RuntimeError("Le certificat CA Proxmox est introuvable.")

    contexte_tls = ssl.create_default_context(cafile=PROXMOX_CA_FILE)
    base_url = PROXMOX_URL.rstrip("/")
    requete = urllib.request.Request(
        f"{base_url}/api2/json/cluster/resources",
        headers={
            "Authorization": (
                f"PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_TOKEN_SECRET}"
            ),
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(
            requete, timeout=10, context=contexte_tls
        ) as reponse:
            donnees = json.load(reponse)
    except Exception as erreur:
        raise RuntimeError(
            f"Impossible de consulter Proxmox ({type(erreur).__name__})."
        ) from None

    if not isinstance(donnees, dict):
        raise RuntimeError("Réponse Proxmox invalide : format inattendu.")

    ressources = donnees.get("data")
    if not isinstance(ressources, list):
        raise RuntimeError(
            "Réponse Proxmox invalide : la liste des ressources est absente ou invalide."
        )

    if any(not isinstance(ressource, dict) for ressource in ressources):
        raise RuntimeError(
            "Réponse Proxmox invalide : une ressource n'est pas un objet."
        )

    noeuds = []
    machines = []

    for ressource in ressources:
        type_ressource = ressource.get("type")

        for champ in ("cpu", "mem", "maxmem"):
            _nombre_proxmox_valide(
                ressource.get(champ), champ
            )

        if type_ressource == "node":
            noeuds.append({
                "nom": ressource.get("node"),
                "etat": ressource.get("status", "inconnu"),
                "cpu_pourcent": (
                    round(ressource["cpu"] * 100, 1)
                    if ressource.get("cpu") is not None else None
                ),
                "memoire_utilisee_mo": (
                    round(ressource["mem"] / 1024**2)
                    if ressource.get("mem") is not None else None
                ),
                "memoire_totale_mo": (
                    round(ressource["maxmem"] / 1024**2)
                    if ressource.get("maxmem") is not None else None
                ),
            })

        elif type_ressource in ("qemu", "lxc"):
            machines.append({
                "type": "VM" if type_ressource == "qemu" else "conteneur",
                "id": ressource.get("vmid"),
                "identifiant": ressource.get("id"),
                "tags": ressource.get("tags"),
                "nom": ressource.get("name"),
                "noeud": ressource.get("node"),
                "etat": ressource.get("status", "inconnu"),
                "cpu_pourcent": (
                    round(ressource["cpu"] * 100, 1)
                    if ressource.get("cpu") is not None else None
                ),
                "memoire_utilisee_mo": (
                    round(ressource["mem"] / 1024**2)
                    if ressource.get("mem") is not None else None
                ),
                "memoire_totale_mo": (
                    round(ressource["maxmem"] / 1024**2)
                    if ressource.get("maxmem") is not None else None
                ),
            })

    machines_par_type = {}
    machines_par_etat = {}
    machines_par_type_et_etat = {}

    for machine in machines:
        type_machine = machine["type"]
        etat_machine = machine["etat"]

        machines_par_type[type_machine] = (
            machines_par_type.get(type_machine, 0) + 1
        )
        machines_par_etat[etat_machine] = (
            machines_par_etat.get(etat_machine, 0) + 1
        )

        if type_machine not in machines_par_type_et_etat:
            machines_par_type_et_etat[type_machine] = {}

        machines_par_type_et_etat[type_machine][etat_machine] = (
            machines_par_type_et_etat[type_machine].get(etat_machine, 0) + 1
        )

    for type_machine in machines_par_type:
        for etat in ("running", "stopped", "unknown"):
            machines_par_type_et_etat.setdefault(
                type_machine, {}
            ).setdefault(etat, 0)

    return {
        "disponible": True,
        "nombre_noeuds": len(noeuds),
        "noeuds": sorted(noeuds, key=lambda n: n["nom"] or ""),
        "nombre_machines": len(machines),
        "machines_par_type": dict(sorted(machines_par_type.items())),
        "machines_par_etat": dict(sorted(machines_par_etat.items())),
        "machines_par_type_et_etat": {
            type_machine: dict(sorted(etats.items()))
            for type_machine, etats in sorted(
                machines_par_type_et_etat.items()
            )
        },
        "machines": sorted(
            machines,
            key=lambda m: (m["noeud"] or "", m["id"] or 0),
        ),
    }


def inventaire_os_proxmox() -> dict:
    """Collecte les informations OS des VM QEMU en fonctionnement, en lecture seule."""
    if not all((PROXMOX_URL, PROXMOX_TOKEN_ID, PROXMOX_TOKEN_SECRET)):
        raise RuntimeError("La configuration Proxmox est absente.")

    if not os.path.isfile(PROXMOX_CA_FILE):
        raise RuntimeError("Le certificat CA Proxmox est introuvable.")

    contexte_tls = ssl.create_default_context(cafile=PROXMOX_CA_FILE)
    base_url = PROXMOX_URL.rstrip("/")
    en_tetes = {
        "Authorization": (
            f"PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_TOKEN_SECRET}"
        ),
        "Accept": "application/json",
    }

    def requete_proxmox(chemin: str) -> dict:
        requete = urllib.request.Request(
            f"{base_url}{chemin}",
            headers=en_tetes,
        )
        with urllib.request.urlopen(
            requete, timeout=10, context=contexte_tls
        ) as reponse:
            donnees = json.load(reponse)

        if not isinstance(donnees, dict) or "data" not in donnees:
            raise RuntimeError("Réponse Proxmox invalide.")

        return donnees

    try:
        donnees = requete_proxmox("/api2/json/cluster/resources")
    except Exception as erreur:
        raise RuntimeError(
            f"Impossible de consulter Proxmox ({type(erreur).__name__})."
        ) from None

    ressources = donnees["data"]
    if not isinstance(ressources, list) or any(
        not isinstance(ressource, dict) for ressource in ressources
    ):
        raise RuntimeError("Réponse Proxmox invalide : ressources incorrectes.")

    machines = []

    for ressource in ressources:
        if (
            ressource.get("type") != "qemu"
            or ressource.get("status") != "running"
        ):
            continue

        vmid = ressource.get("vmid")
        noeud = ressource.get("node")
        machine = {
            "vmid": vmid,
            "nom": ressource.get("name"),
            "noeud": noeud,
            "etat_collecte": "indisponible",
            "nom_os": None,
            "version_os": None,
            "version_id_os": None,
            "noyau": None,
        }

        if (
            isinstance(vmid, bool)
            or not isinstance(vmid, int)
            or vmid <= 0
            or not isinstance(noeud, str)
            or not noeud
            or any(
                not (caractere.isascii() and (
                    caractere.isalnum() or caractere in "_.-"
                ))
                for caractere in noeud
            )
        ):
            machine["etat_collecte"] = "identifiants_invalides"
            machines.append(machine)
            continue

        try:
            informations = requete_proxmox(
                f"/api2/json/nodes/{noeud}/qemu/{vmid}/agent/get-osinfo"
            )
            os_info = informations["data"]

            if not isinstance(os_info, dict):
                machine["etat_collecte"] = "reponse_os_invalide"
            else:
                machine.update({
                    "nom_os": os_info.get("pretty-name") or os_info.get("name"),
                    "version_os": os_info.get("version") or os_info.get("version-id"),
                    "version_id_os": os_info.get("version-id"),
                    "noyau": os_info.get("kernel-release"),
                    "etat_collecte": (
                        "collecte_ok"
                        if os_info.get("name") or os_info.get("pretty-name")
                        else "os_inconnu"
                    ),
                })
        except urllib.error.HTTPError as erreur:
            if erreur.code in (401, 403):
                machine["etat_collecte"] = "erreur_api"
            else:
                machine["etat_collecte"] = "agent_indisponible"
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            machine["etat_collecte"] = "agent_indisponible"
        except (json.JSONDecodeError, RuntimeError):
            machine["etat_collecte"] = "reponse_os_invalide"

        machines.append(machine)

    return {
        "disponible": True,
        "nombre_vm_qemu_en_fonctionnement": len(machines),
        "nombre_os_identifies": sum(
            machine["etat_collecte"] == "collecte_ok"
            for machine in machines
        ),
        "machines": sorted(
            machines,
            key=lambda machine: (
                machine["noeud"] or "",
                machine["vmid"] if isinstance(machine["vmid"], int) else 0,
            ),
        ),
    }

OUTILS = {
    "heure_actuelle": heure_actuelle,
    "heure_dans": heure_dans,
    "etat_systeme": etat_systeme,
    "etat_gpu": etat_gpu,
    "etat_ollama": etat_ollama,
    "etat_home_assistant": etat_home_assistant,
    "etat_proxmox": etat_proxmox,
    "inventaire_os_proxmox": inventaire_os_proxmox,
}

DEFINITIONS_OUTILS = [
    {
        "type": "function",
        "function": {
            "name": "heure_actuelle",
            "description": "Retourne l heure actuelle.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "heure_dans",
            "description": "Retourne l heure dans un nombre de minutes donné.",
            "parameters": {
                "type": "object",
                "properties": {
                    "minutes": {
                        "type": "integer",
                        "description": "Nombre de minutes à ajouter à l heure actuelle.",
                    },
                },
                "required": ["minutes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "etat_systeme",
            "description": "Retourne l état actuel du système.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "etat_gpu",
            "description": "Retourne l état des GPU NVIDIA visibles par le système.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "etat_ollama",
            "description": "Retourne l état du serveur Ollama, les modèles disponibles et les modèles actuellement actifs.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "etat_home_assistant",
            "description": (
                "Retourne la version de Home Assistant, le nombre d'entités "
                "et leur répartition par domaine. Cet outil est en lecture seule."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "etat_proxmox",
            "description": (
                "Consulte en lecture seule le cluster Proxmox. "
                "Les champs type, id, nom, noeud et etat proviennent "
                "des données de l'API. Le type vaut VM ou conteneur "
                "et ne doit jamais être déduit de l'état. Les états "
                "possibles comprennent running, stopped et unknown. "
                "Un état unknown n'est pas un état stopped. "
                "Si le nom vaut null, il est inconnu et ne doit pas "
                "être inventé. Pour les totaux, compte les entrées "
                "de machines et classe-les selon leur type et leur "
                "état. Ne déduis pas de machines supplémentaires "
                "à partir des tags ou des identifiants."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inventaire_os_proxmox",
            "description": (
                "Collecte en lecture seule les informations du système "
                "d'exploitation des VM QEMU en fonctionnement via leur "
                "agent invité Proxmox. Une collecte peut être indisponible "
                "si l'agent ne répond pas. Cet outil ne détecte pas les CVE "
                "et ne couvre pas les conteneurs LXC."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },

]
