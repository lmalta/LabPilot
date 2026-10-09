import json
from unittest.mock import patch
from labpilot.agent import Agent, MAX_CYCLES_OUTILS, executer_outil
from labpilot.tools import etat_gpu, etat_ollama, etat_home_assistant


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


def test_etat_gpu():
    sortie = (
        "0, NVIDIA GeForce RTX 3060, 12288, 5491, 6422, "
        "0, 34, 11.41\n"
    )

    with patch("labpilot.tools.subprocess.run") as executer:
        executer.return_value.stdout = sortie

        resultat = etat_gpu()

    assert resultat == [
        {
            "index": 0,
            "nom": "NVIDIA GeForce RTX 3060",
            "memoire_totale_mo": 12288,
            "memoire_utilisee_mo": 5491,
            "memoire_disponible_mo": 6422,
            "utilisation_gpu_pourcent": 0,
            "temperature_c": 34,
            "consommation_w": 11.41,
        }
    ]

    executer.assert_called_once()


def test_etat_gpu_plusieurs_gpu():
    sortie = (
        "0, NVIDIA GeForce RTX 3060, 12288, 5491, 6422, 0, 34, 11.41\n"
        "1, NVIDIA GeForce RTX 4090, 24576, 1200, 23376, 12, 40, 80.50\n"
    )

    with patch("labpilot.tools.subprocess.run") as executer:
        executer.return_value.stdout = sortie

        resultat = etat_gpu()

    assert resultat == [
        {
            "index": 0,
            "nom": "NVIDIA GeForce RTX 3060",
            "memoire_totale_mo": 12288,
            "memoire_utilisee_mo": 5491,
            "memoire_disponible_mo": 6422,
            "utilisation_gpu_pourcent": 0,
            "temperature_c": 34,
            "consommation_w": 11.41,
        },
        {
            "index": 1,
            "nom": "NVIDIA GeForce RTX 4090",
            "memoire_totale_mo": 24576,
            "memoire_utilisee_mo": 1200,
            "memoire_disponible_mo": 23376,
            "utilisation_gpu_pourcent": 12,
            "temperature_c": 40,
            "consommation_w": 80.50,
        },
    ]

    executer.assert_called_once()


def test_etat_gpu_erreur_nvidia_smi():
    with patch(
        "labpilot.tools.subprocess.run",
        side_effect=FileNotFoundError("nvidia-smi introuvable"),
    ):
        resultat = executer_outil(
            {
                "function": {
                    "name": "etat_gpu",
                    "arguments": {},
                }
            }
        )

    assert resultat == {
        "erreur": "FileNotFoundError",
        "message": "nvidia-smi introuvable",
    }


def test_etat_ollama_erreur():
    with patch(
        "labpilot.tools.urllib.request.urlopen",
        side_effect=ConnectionError("Ollama est inaccessible"),
    ):
        resultat = executer_outil(
            {
                "function": {
                    "name": "etat_ollama",
                    "arguments": {},
                }
            }
        )

    assert resultat == {
        "erreur": "ConnectionError",
        "message": "Ollama est inaccessible",
    }


def test_etat_ollama():
    reponses = [
        {"version": "0.34.2"},
        {
            "models": [
                {"name": "qwen3-vl:8b"},
                {"name": "qwen3:14b"},
                {"name": "qwen3:8b"},
            ]
        },
        {
            "models": [
                {"name": "qwen3:8b"},
            ]
        },
    ]

    def reponse_http(*args, **kwargs):
        reponse = reponses.pop(0)

        class Reponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self):
                return json.dumps(reponse).encode()

        return Reponse()

    with patch(
        "labpilot.tools.urllib.request.urlopen",
        side_effect=reponse_http,
    ) as urlopen:
        resultat = etat_ollama()

    assert [appel.args[0] for appel in urlopen.call_args_list] == [
        "http://127.0.0.1:11434/api/version",
        "http://127.0.0.1:11434/api/tags",
        "http://127.0.0.1:11434/api/ps",
    ]

    assert resultat == {
        "disponible": True,
        "version": "0.34.2",
        "modeles": [
            "qwen3-vl:8b",
            "qwen3:14b",
            "qwen3:8b",
        ],
        "modeles_actifs": [
            "qwen3:8b",
        ],
    }


def test_etat_home_assistant():
    reponses = [
        {"version": "2026.9.2"},
        [
            {"entity_id": "sensor.temperature"},
            {"entity_id": "sensor.humidite"},
            {"entity_id": "light.salon"},
        ],
    ]

    def reponse_http(*args, **kwargs):
        resultat = reponses.pop(0)

        class Reponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self):
                return json.dumps(resultat).encode()

        return Reponse()

    with patch(
        "labpilot.tools.urllib.request.urlopen",
        side_effect=reponse_http,
    ) as urlopen:
        resultat = etat_home_assistant()

    assert resultat == {
        "disponible": True,
        "version": "2026.9.2",
        "nombre_entites": 3,
        "entites_par_domaine": {
            "light": 1,
            "sensor": 2,
        },
    }

    assert urlopen.call_count == 2


def test_etat_home_assistant_erreur_http():
    jeton_fictif = "JETON_SECRET_TEST"

    with (
        patch("labpilot.tools.HOME_ASSISTANT_URL", "http://home-assistant"),
        patch("labpilot.tools.HOME_ASSISTANT_TOKEN", jeton_fictif),
        patch(
            "labpilot.tools.urllib.request.urlopen",
            side_effect=ConnectionError(jeton_fictif),
        ),
    ):
        resultat = executer_outil(
            {
                "function": {
                    "name": "etat_home_assistant",
                    "arguments": {},
                }
            }
        )

    assert resultat["erreur"] == "RuntimeError"
    assert jeton_fictif not in resultat["message"]


def test_etat_home_assistant_configuration_absente():
    with (
        patch("labpilot.tools.HOME_ASSISTANT_URL", None),
        patch("labpilot.tools.HOME_ASSISTANT_TOKEN", None),
        patch("labpilot.tools.urllib.request.urlopen") as urlopen,
    ):
        resultat = executer_outil(
            {
                "function": {
                    "name": "etat_home_assistant",
                    "arguments": {},
                }
            }
        )

    assert resultat["erreur"] == "RuntimeError"
    urlopen.assert_not_called()
