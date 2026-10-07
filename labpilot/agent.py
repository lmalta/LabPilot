import json
from .ollama import interroger_ollama
from .tools import OUTILS


def executer_outil(tool_call: dict) -> str:
    nom_outil = tool_call["function"]["name"]
    arguments = tool_call["function"]["arguments"]
    outil = OUTILS[nom_outil]

    return outil(**arguments)


class Agent:
    def __init__(self) -> None:
        self.historique = [
            {
                "role": "system",
                "content": (
                    "Tu es LabPilot, un agent local. "
                    "Utilise les outils disponibles lorsque cela est pertinent. "
                    "Les outils peuvent retourner des données techniques ou brutes. "
                    "Interprète leurs résultats et présente-les naturellement à l utilisateur. "
                    "Ne montre pas inutilement les formats techniques internes."
                ),
            }
        ]

    def executer(self, message: str) -> str:
        self.historique.append(
            {
                "role": "user",
                "content": message,
            }
        )

        for _ in range(10):
            reponse = interroger_ollama(self.historique)

            self.historique.append(reponse)

            if "tool_calls" not in reponse:
                return reponse["content"]

            for tool_call in reponse["tool_calls"]:
                resultat = executer_outil(tool_call)

                if not isinstance(resultat, str):
                    resultat = json.dumps(resultat, ensure_ascii=False)

                self.historique.append(
                    {
                        "role": "tool",
                        "tool_name": tool_call["function"]["name"],
                        "content": resultat,
                    }
                )

        return "Le nombre maximal d appels d outils a été atteint."
