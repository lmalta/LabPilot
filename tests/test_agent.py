from unittest.mock import patch
from labpilot.agent import Agent, MAX_CYCLES_OUTILS


def test_creation_agent():
    agent = Agent()

    assert agent.historique


def test_limite_boucle_appels_outils():
    agent = Agent()

    reponse_outil = {
        "role": "assistant",
        "tool_calls": [
            {
                "function": {
                    "name": "heure_actuelle",
                    "arguments": {},
                }
            }
        ],
    }

    with patch("labpilot.agent.interroger_ollama", return_value=reponse_outil) as ollama:
        resultat = agent.executer("Teste la protection contre une boucle.")

    assert resultat == "Le nombre maximal d appels d outils a été atteint."
    assert ollama.call_count == MAX_CYCLES_OUTILS