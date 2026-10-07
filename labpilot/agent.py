from .ollama import interroger_ollama


class Agent:
    def __init__(self) -> None:
        self.historique = []

    def executer(self, message: str) -> str:
        self.historique.append(
            {
                "role": "user",
                "content": message,
            }
        )

        reponse = interroger_ollama(self.historique)

        self.historique.append(
            {
                "role": "assistant",
                "content": reponse,
            }
        )

        return reponse
