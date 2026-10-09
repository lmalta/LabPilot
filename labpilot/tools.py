import os
import platform
import subprocess
import json
import urllib.request
from datetime import datetime, timedelta
from labpilot.configuration import HOME_ASSISTANT_URL, HOME_ASSISTANT_TOKEN


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

OUTILS = {
    "heure_actuelle": heure_actuelle,
    "heure_dans": heure_dans,
    "etat_systeme": etat_systeme,
    "etat_gpu": etat_gpu,
    "etat_ollama": etat_ollama,
    "etat_home_assistant": etat_home_assistant,
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
]
