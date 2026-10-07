import os
import platform
from datetime import datetime, timedelta


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

OUTILS = {
    "heure_actuelle": heure_actuelle,
    "heure_dans": heure_dans,
    "etat_systeme": etat_systeme,
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
]
