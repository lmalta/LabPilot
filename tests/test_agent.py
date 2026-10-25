import json
import pytest
from unittest.mock import patch
from labpilot.agent import Agent, MAX_CYCLES_OUTILS, executer_outil
from labpilot.tools import etat_gpu, etat_ollama, etat_home_assistant
from labpilot.tools import etat_proxmox, DEFINITIONS_OUTILS


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

def test_etat_proxmox():
    ressources = [
        {
            "type": "node",
            "node": "maltas",
            "status": "online",
            "cpu": 0.25,
            "mem": 2 * 1024**3,
            "maxmem": 8 * 1024**3,
        },
        {
            "type": "node",
            "node": "Malta-D",
            "status": "offline",
        },
        {
            "type": "qemu",
            "id": "qemu/300",
            "vmid": 300,
            "name": "haos18-2",
            "node": "maltas",
            "status": "running",
            "tags": "test;linux",
            "cpu": 0.10,
            "mem": 1024**3,
            "maxmem": 2 * 1024**3,
        },
        {
            "type": "lxc",
            "id": "lxc/200",
            "vmid": 200,
            "name": "conteneur-test",
            "node": "Malta-D",
            "status": "stopped",
            "tags": None,
        },
    ]

    class Reponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return json.dumps({"data": ressources}).encode()

    with (
        patch("labpilot.tools.PROXMOX_URL", "https://proxmox-test:8006"),
        patch("labpilot.tools.PROXMOX_TOKEN_ID", "test@pve!readonly"),
        patch("labpilot.tools.PROXMOX_TOKEN_SECRET", "secret-fictif"),
        patch("labpilot.tools.os.path.isfile", return_value=True),
        patch(
            "labpilot.tools.ssl.create_default_context"
        ) as create_context,
        patch(
            "labpilot.tools.urllib.request.urlopen",
            return_value=Reponse(),
        ) as urlopen,
    ):
        resultat = etat_proxmox()

    create_context.assert_called_once_with(
        cafile=etat_proxmox.__globals__["PROXMOX_CA_FILE"]
    )

    requete = urlopen.call_args.args[0]
    assert requete.full_url == (
        "https://proxmox-test:8006/api2/json/cluster/resources"
    )
    assert requete.get_header("Authorization") == (
        "PVEAPIToken=test@pve!readonly=secret-fictif"
    )
    assert requete.get_header("Accept") == "application/json"
    assert urlopen.call_args.kwargs["timeout"] == 10
    assert urlopen.call_args.kwargs["context"] is create_context.return_value

    assert resultat["disponible"] is True
    assert resultat["nombre_noeuds"] == 2
    assert resultat["nombre_machines"] == 2
    assert resultat["machines_par_type"] == {
        "VM": 1,
        "conteneur": 1,
    }
    assert resultat["machines_par_etat"] == {
        "running": 1,
        "stopped": 1,
    }
    assert resultat["machines_par_type_et_etat"] == {
        "VM": {
            "running": 1,
            "stopped": 0,
            "unknown": 0,
        },
        "conteneur": {
            "running": 0,
            "stopped": 1,
            "unknown": 0,
        },
    }

    maltas = next(n for n in resultat["noeuds"] if n["nom"] == "maltas")
    assert maltas["etat"] == "online"
    assert maltas["cpu_pourcent"] == 25.0
    assert maltas["memoire_utilisee_mo"] == 2048
    assert maltas["memoire_totale_mo"] == 8192

    malta_d = next(n for n in resultat["noeuds"] if n["nom"] == "Malta-D")
    assert malta_d["etat"] == "offline"
    assert malta_d["cpu_pourcent"] is None

    vm = next(m for m in resultat["machines"] if m["id"] == 300)
    assert vm["type"] == "VM"
    assert vm["nom"] == "haos18-2"
    assert vm["memoire_utilisee_mo"] == 1024
    assert vm["identifiant"] == "qemu/300"
    assert vm["tags"] == "test;linux"

    conteneur = next(m for m in resultat["machines"] if m["id"] == 200)
    assert conteneur["type"] == "conteneur"
    assert conteneur["etat"] == "stopped"
    assert conteneur["identifiant"] == "lxc/200"
    assert conteneur["tags"] is None

    urlopen.assert_called_once()


def test_etat_proxmox_configuration_absente():
    with (
        patch("labpilot.tools.PROXMOX_URL", None),
        patch("labpilot.tools.PROXMOX_TOKEN_ID", None),
        patch("labpilot.tools.PROXMOX_TOKEN_SECRET", None),
        patch("labpilot.tools.urllib.request.urlopen") as urlopen,
    ):
        resultat = executer_outil({
            "function": {
                "name": "etat_proxmox",
                "arguments": {},
            }
        })

    assert resultat["erreur"] == "RuntimeError"
    urlopen.assert_not_called()


def test_etat_proxmox_erreur_api():
    with (
        patch("labpilot.tools.PROXMOX_URL", "https://proxmox-test:8006"),
        patch("labpilot.tools.PROXMOX_TOKEN_ID", "test@pve!readonly"),
        patch("labpilot.tools.PROXMOX_TOKEN_SECRET", "secret-fictif"),
        patch("labpilot.tools.os.path.isfile", return_value=True),
        patch("labpilot.tools.ssl.create_default_context"),
        patch(
            "labpilot.tools.urllib.request.urlopen",
            side_effect=ConnectionError("secret-fictif"),
        ),
    ):
        resultat = executer_outil({
            "function": {
                "name": "etat_proxmox",
                "arguments": {},
            }
        })

    assert resultat["erreur"] == "RuntimeError"
    assert "secret-fictif" not in resultat["message"]


def test_etat_proxmox_authentification_refusee():
    from urllib.error import HTTPError

    with (
        patch("labpilot.tools.PROXMOX_URL", "https://proxmox-test:8006"),
        patch("labpilot.tools.PROXMOX_TOKEN_ID", "test@pve!readonly"),
        patch("labpilot.tools.PROXMOX_TOKEN_SECRET", "secret-fictif"),
        patch("labpilot.tools.os.path.isfile", return_value=True),
        patch("labpilot.tools.ssl.create_default_context"),
        patch(
            "labpilot.tools.urllib.request.urlopen",
            side_effect=HTTPError(
                "https://proxmox-test:8006/api2/json/cluster/resources",
                401,
                "Unauthorized secret-fictif",
                {},
                None,
            ),
        ),
    ):
        resultat = executer_outil({
            "function": {
                "name": "etat_proxmox",
                "arguments": {},
            }
        })

    assert resultat["erreur"] == "RuntimeError"
    assert "secret-fictif" not in resultat["message"]


def test_etat_proxmox_permissions_insuffisantes():
    from urllib.error import HTTPError

    with (
        patch("labpilot.tools.PROXMOX_URL", "https://proxmox-test:8006"),
        patch("labpilot.tools.PROXMOX_TOKEN_ID", "test@pve!readonly"),
        patch("labpilot.tools.PROXMOX_TOKEN_SECRET", "secret-fictif"),
        patch("labpilot.tools.os.path.isfile", return_value=True),
        patch("labpilot.tools.ssl.create_default_context"),
        patch(
            "labpilot.tools.urllib.request.urlopen",
            side_effect=HTTPError(
                "https://proxmox-test:8006/api2/json/cluster/resources",
                403,
                "Forbidden secret-fictif",
                {},
                None,
            ),
        ),
    ):
        resultat = executer_outil({
            "function": {
                "name": "etat_proxmox",
                "arguments": {},
            }
        })

    assert resultat["erreur"] == "RuntimeError"
    assert "secret-fictif" not in resultat["message"]


def test_etat_proxmox_certificat_ca_absent():
    with (
        patch("labpilot.tools.PROXMOX_URL", "https://proxmox-test:8006"),
        patch("labpilot.tools.PROXMOX_TOKEN_ID", "test@pve!readonly"),
        patch("labpilot.tools.PROXMOX_TOKEN_SECRET", "secret-fictif"),
        patch("labpilot.tools.os.path.isfile", return_value=False),
        patch("labpilot.tools.ssl.create_default_context") as create_context,
        patch("labpilot.tools.urllib.request.urlopen") as urlopen,
    ):
        resultat = executer_outil({
            "function": {
                "name": "etat_proxmox",
                "arguments": {},
            }
        })

    assert resultat["erreur"] == "RuntimeError"
    assert "certificat CA Proxmox est introuvable" in resultat["message"]
    create_context.assert_not_called()
    urlopen.assert_not_called()


def test_etat_proxmox_reponse_data_non_liste():
    with (
        patch("labpilot.tools.PROXMOX_URL", "https://proxmox-test:8006"),
        patch("labpilot.tools.PROXMOX_TOKEN_ID", "test@pve!readonly"),
        patch("labpilot.tools.PROXMOX_TOKEN_SECRET", "secret-fictif"),
        patch("labpilot.tools.os.path.isfile", return_value=True),
        patch("labpilot.tools.ssl.create_default_context"),
        patch("labpilot.tools.urllib.request.urlopen"),
        patch("labpilot.tools.json.load", return_value={"data": "invalide"}),
    ):
        resultat = executer_outil({
            "function": {
                "name": "etat_proxmox",
                "arguments": {},
            }
        })

    assert resultat["erreur"] == "RuntimeError"


def test_etat_proxmox_ressource_invalide():
    with (
        patch("labpilot.tools.PROXMOX_URL", "https://proxmox-test:8006"),
        patch("labpilot.tools.PROXMOX_TOKEN_ID", "test@pve!readonly"),
        patch("labpilot.tools.PROXMOX_TOKEN_SECRET", "secret-fictif"),
        patch("labpilot.tools.os.path.isfile", return_value=True),
        patch("labpilot.tools.ssl.create_default_context"),
        patch("labpilot.tools.urllib.request.urlopen"),
        patch("labpilot.tools.json.load", return_value={"data": ["invalide"]}),
    ):
        resultat = executer_outil({
            "function": {
                "name": "etat_proxmox",
                "arguments": {},
            }
        })

    assert resultat["erreur"] == "RuntimeError"


def test_etat_proxmox_cpu_invalide():
    from unittest.mock import mock_open

    donnees_invalides = {
        "data": [
            {
                "type": "node",
                "node": "pve1",
                "status": "online",
                "cpu": "inconnu",
                "mem": 1024,
                "maxmem": 2048,
            }
        ]
    }

    with (
        patch("labpilot.tools.PROXMOX_URL", "https://proxmox-test:8006"),
        patch("labpilot.tools.PROXMOX_TOKEN_ID", "test@pve!readonly"),
        patch("labpilot.tools.PROXMOX_TOKEN_SECRET", "secret-fictif"),
        patch("labpilot.tools.os.path.isfile", return_value=True),
        patch("labpilot.tools.ssl.create_default_context"),
        patch("labpilot.tools.urllib.request.urlopen"),
        patch("labpilot.tools.json.load", return_value=donnees_invalides),
    ):
        resultat = executer_outil({
            "function": {
                "name": "etat_proxmox",
                "arguments": {},
            }
        })

    assert resultat["erreur"] == "RuntimeError"
    assert "inconnu" not in resultat["message"]


def test_etat_proxmox_memoire_invalide():
    for champ in ("mem", "maxmem"):
        donnees_invalides = {
            "data": [
                {
                    "type": "node",
                    "node": "pve1",
                    "status": "online",
                    "cpu": 0.25,
                    "mem": 1024,
                    "maxmem": 2048,
                    champ: "invalide",
                }
            ]
        }

        with (
            patch("labpilot.tools.PROXMOX_URL", "https://proxmox-test:8006"),
            patch("labpilot.tools.PROXMOX_TOKEN_ID", "test@pve!readonly"),
            patch("labpilot.tools.PROXMOX_TOKEN_SECRET", "secret-fictif"),
            patch("labpilot.tools.os.path.isfile", return_value=True),
            patch("labpilot.tools.ssl.create_default_context"),
            patch("labpilot.tools.urllib.request.urlopen"),
            patch("labpilot.tools.json.load", return_value=donnees_invalides),
        ):
            resultat = executer_outil({
                "function": {
                    "name": "etat_proxmox",
                    "arguments": {},
                }
            })

        assert resultat["erreur"] == "RuntimeError"
        assert champ in resultat["message"]


def test_etat_proxmox_cpu_nan():
    donnees_invalides = {
        "data": [
            {
                "type": "node",
                "node": "pve1",
                "status": "online",
                "cpu": float("nan"),
                "mem": 1024,
                "maxmem": 2048,
            }
        ]
    }

    with (
        patch("labpilot.tools.PROXMOX_URL", "https://proxmox-test:8006"),
        patch("labpilot.tools.PROXMOX_TOKEN_ID", "test@pve!readonly"),
        patch("labpilot.tools.PROXMOX_TOKEN_SECRET", "secret-fictif"),
        patch("labpilot.tools.os.path.isfile", return_value=True),
        patch("labpilot.tools.ssl.create_default_context"),
        patch("labpilot.tools.urllib.request.urlopen"),
        patch("labpilot.tools.json.load", return_value=donnees_invalides),
    ):
        resultat = executer_outil({
            "function": {
                "name": "etat_proxmox",
                "arguments": {},
            }
        })

    assert resultat["erreur"] == "RuntimeError"
    assert "cpu" in resultat["message"]


def test_inventaire_os_proxmox_recupere_os_vm():
    from labpilot.tools import inventaire_os_proxmox

    ressources = {
        "data": [
            {
                "type": "qemu",
                "vmid": 300,
                "name": "haos18-2",
                "node": "pve1",
                "status": "running",
            },
            {
                "type": "qemu",
                "vmid": 301,
                "name": "vm-arretee",
                "node": "pve1",
                "status": "stopped",
            },
            {
                "type": "lxc",
                "vmid": 200,
                "name": "conteneur-test",
                "node": "pve1",
                "status": "running",
            },
        ]
    }
    informations_os = {
        "data": {
            "id": "debian",
            "name": "Debian GNU/Linux",
            "pretty-name": "Debian GNU/Linux 12 (bookworm)",
            "version-id": "12",
            "kernel-release": "6.8.12",
        }
    }

    reponse_ressources = type(
        "Reponse",
        (),
        {"__enter__": lambda self: self, "__exit__": lambda *args: None},
    )()
    reponse_os = type(
        "Reponse",
        (),
        {"__enter__": lambda self: self, "__exit__": lambda *args: None},
    )()

    with (
        patch("labpilot.tools.PROXMOX_URL", "https://proxmox-test:8006"),
        patch("labpilot.tools.PROXMOX_TOKEN_ID", "test@pve!readonly"),
        patch("labpilot.tools.PROXMOX_TOKEN_SECRET", "secret-fictif"),
        patch("labpilot.tools.os.path.isfile", return_value=True),
        patch("labpilot.tools.ssl.create_default_context"),
        patch(
            "labpilot.tools.urllib.request.urlopen",
            side_effect=[reponse_ressources, reponse_os],
        ) as urlopen,
        patch(
            "labpilot.tools.json.load",
            side_effect=[ressources, informations_os],
        ),
    ):
        resultat = inventaire_os_proxmox()

    assert resultat["machines"][0]["vmid"] == 300
    assert resultat["machines"][0]["nom_os"] == "Debian GNU/Linux 12 (bookworm)"
    assert resultat["machines"][0]["version_os"] == "12"
    assert len(resultat["machines"]) == 1
    assert urlopen.call_count == 2




def test_inventaire_os_proxmox_continue_si_agent_indisponible():
    from urllib.error import URLError
    from labpilot.tools import inventaire_os_proxmox

    ressources = {
        "data": [
            {
                "type": "qemu",
                "vmid": 300,
                "name": "haos18-2",
                "node": "pve1",
                "status": "running",
            },
            {
                "type": "qemu",
                "vmid": 302,
                "name": "vm-linux",
                "node": "pve1",
                "status": "running",
            },
        ]
    }
    informations_os = {
        "data": {
            "name": "Ubuntu",
            "pretty-name": "Ubuntu 24.04 LTS",
            "version-id": "24.04",
            "kernel-release": "6.8.0",
        }
    }

    reponse = type(
        "Reponse",
        (),
        {"__enter__": lambda self: self, "__exit__": lambda *args: None},
    )()

    with (
        patch("labpilot.tools.PROXMOX_URL", "https://proxmox-test:8006"),
        patch("labpilot.tools.PROXMOX_TOKEN_ID", "test@pve!readonly"),
        patch("labpilot.tools.PROXMOX_TOKEN_SECRET", "secret-fictif"),
        patch("labpilot.tools.os.path.isfile", return_value=True),
        patch("labpilot.tools.ssl.create_default_context"),
        patch(
            "labpilot.tools.urllib.request.urlopen",
            side_effect=[reponse, URLError("agent indisponible"), reponse],
        ),
        patch(
            "labpilot.tools.json.load",
            side_effect=[ressources, informations_os],
        ),
    ):
        resultat = inventaire_os_proxmox()

    machines = {machine["vmid"]: machine for machine in resultat["machines"]}

    assert machines[300]["etat_collecte"] == "agent_indisponible"
    assert machines[300]["nom_os"] is None
    assert machines[302]["etat_collecte"] == "collecte_ok"
    assert machines[302]["nom_os"] == "Ubuntu 24.04 LTS"
    assert resultat["nombre_os_identifies"] == 1


def test_inventaire_os_proxmox_authentification_refusee():
    from urllib.error import HTTPError
    from labpilot.tools import inventaire_os_proxmox

    ressources = {
        "data": [
            {
                "type": "qemu",
                "vmid": 300,
                "name": "vm-test",
                "node": "pve1",
                "status": "running",
            }
        ]
    }

    reponse = type(
        "Reponse",
        (),
        {"__enter__": lambda self: self, "__exit__": lambda *args: None},
    )()

    with (
        patch("labpilot.tools.PROXMOX_URL", "https://proxmox-test:8006"),
        patch("labpilot.tools.PROXMOX_TOKEN_ID", "test@pve!readonly"),
        patch("labpilot.tools.PROXMOX_TOKEN_SECRET", "secret-fictif"),
        patch("labpilot.tools.os.path.isfile", return_value=True),
        patch("labpilot.tools.ssl.create_default_context"),
        patch(
            "labpilot.tools.urllib.request.urlopen",
            side_effect=[
                reponse,
                HTTPError(
                    "https://proxmox-test:8006/api2/json/nodes/pve1/qemu/300/agent/get-osinfo",
                    401,
                    "Unauthorized secret-fictif",
                    {},
                    None,
                ),
            ],
        ),
        patch(
            "labpilot.tools.json.load",
            return_value=ressources,
        ),
    ):
        resultat = inventaire_os_proxmox()

    assert resultat["machines"][0]["etat_collecte"] == "erreur_api"


def test_inventaire_os_proxmox_permissions_insuffisantes():
    from urllib.error import HTTPError
    from labpilot.tools import inventaire_os_proxmox

    ressources = {
        "data": [
            {
                "type": "qemu",
                "vmid": 300,
                "name": "vm-test",
                "node": "pve1",
                "status": "running",
            }
        ]
    }

    reponse = type(
        "Reponse",
        (),
        {"__enter__": lambda self: self, "__exit__": lambda *args: None},
    )()

    with (
        patch("labpilot.tools.PROXMOX_URL", "https://proxmox-test:8006"),
        patch("labpilot.tools.PROXMOX_TOKEN_ID", "test@pve!readonly"),
        patch("labpilot.tools.PROXMOX_TOKEN_SECRET", "secret-fictif"),
        patch("labpilot.tools.os.path.isfile", return_value=True),
        patch("labpilot.tools.ssl.create_default_context"),
        patch(
            "labpilot.tools.urllib.request.urlopen",
            side_effect=[
                reponse,
                HTTPError(
                    "https://proxmox-test:8006/api2/json/nodes/pve1/qemu/300/agent/get-osinfo",
                    403,
                    "Forbidden",
                    {},
                    None,
                ),
            ],
        ),
        patch(
            "labpilot.tools.json.load",
            return_value=ressources,
        ),
    ):
        resultat = inventaire_os_proxmox()

    machine = resultat["machines"][0]
    assert machine["etat_collecte"] == "erreur_api"
    assert machine["nom_os"] is None
    assert resultat["nombre_os_identifies"] == 0


def test_inventaire_os_proxmox_reponse_os_invalide():
    from labpilot.tools import inventaire_os_proxmox

    ressources = {
        "data": [
            {
                "type": "qemu",
                "vmid": 300,
                "name": "vm-test",
                "node": "pve1",
                "status": "running",
            }
        ]
    }

    reponse = type(
        "Reponse",
        (),
        {"__enter__": lambda self: self, "__exit__": lambda *args: None},
    )()

    with (
        patch("labpilot.tools.PROXMOX_URL", "https://proxmox-test:8006"),
        patch("labpilot.tools.PROXMOX_TOKEN_ID", "test@pve!readonly"),
        patch("labpilot.tools.PROXMOX_TOKEN_SECRET", "secret-fictif"),
        patch("labpilot.tools.os.path.isfile", return_value=True),
        patch("labpilot.tools.ssl.create_default_context"),
        patch(
            "labpilot.tools.urllib.request.urlopen",
            side_effect=[reponse, reponse],
        ),
        patch(
            "labpilot.tools.json.load",
            side_effect=[ressources, ValueError("JSON invalide")],
        ),
    ):
        resultat = inventaire_os_proxmox()

    machine = resultat["machines"][0]
    assert machine["etat_collecte"] == "reponse_os_invalide"
    assert machine["nom_os"] is None
    assert resultat["nombre_os_identifies"] == 0


def test_inventaire_os_proxmox_os_inconnu():
    from labpilot.tools import inventaire_os_proxmox

    ressources = {
        "data": [
            {
                "type": "qemu",
                "vmid": 300,
                "name": "vm-test",
                "node": "pve1",
                "status": "running",
            }
        ]
    }

    reponse = type(
        "Reponse",
        (),
        {"__enter__": lambda self: self, "__exit__": lambda *args: None},
    )()

    with (
        patch("labpilot.tools.PROXMOX_URL", "https://proxmox-test:8006"),
        patch("labpilot.tools.PROXMOX_TOKEN_ID", "test@pve!readonly"),
        patch("labpilot.tools.PROXMOX_TOKEN_SECRET", "secret-fictif"),
        patch("labpilot.tools.os.path.isfile", return_value=True),
        patch("labpilot.tools.ssl.create_default_context"),
        patch(
            "labpilot.tools.urllib.request.urlopen",
            side_effect=[reponse, reponse],
        ),
        patch(
            "labpilot.tools.json.load",
            side_effect=[ressources, {"data": {}}],
        ),
    ):
        resultat = inventaire_os_proxmox()

    machine = resultat["machines"][0]
    assert machine["etat_collecte"] == "os_inconnu"
    assert machine["nom_os"] is None
    assert machine["version_os"] is None
    assert resultat["nombre_os_identifies"] == 0


def test_inventaire_os_proxmox_erreur_connexion():
    from labpilot.tools import inventaire_os_proxmox

    with (
        patch("labpilot.tools.PROXMOX_URL", "https://proxmox-test:8006"),
        patch("labpilot.tools.PROXMOX_TOKEN_ID", "test@pve!readonly"),
        patch("labpilot.tools.PROXMOX_TOKEN_SECRET", "secret-fictif"),
        patch("labpilot.tools.os.path.isfile", return_value=True),
        patch("labpilot.tools.ssl.create_default_context"),
        patch(
            "labpilot.tools.urllib.request.urlopen",
            side_effect=ConnectionError("secret-fictif"),
        ),
    ):
        with pytest.raises(RuntimeError) as erreur:
            inventaire_os_proxmox()

    assert "secret-fictif" not in str(erreur.value)
    assert "ConnectionError" in str(erreur.value)
