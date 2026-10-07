from datetime import datetime, timedelta


def heure_actuelle() -> str:
    return datetime.now().astimezone().isoformat()


def heure_dans(minutes: int) -> str:
    return (datetime.now().astimezone() + timedelta(minutes=minutes)).isoformat()


OUTILS = {
    "heure_actuelle": heure_actuelle,
    "heure_dans": heure_dans,
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
]
