import json
import pytest
from unittest.mock import patch
from labpilot.agent import Agent, MAX_CYCLES_OUTILS, executer_outil
from labpilot.tools import etat_gpu, etat_ollama, etat_home_assistant
from labpilot.tools import etat_proxmox, DEFINITIONS_OUTILS, audit_cve_proxmox, OUTILS


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
            "result": {
                "id": "debian",
                "name": "Debian GNU/Linux",
                "pretty-name": "Debian GNU/Linux 13 (trixie)",
                "version": "13 (trixie)",
                "version-id": "13",
                "kernel-release": "6.12.63+deb13-amd64",
            }
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
    assert resultat["machines"][0]["nom_os"] == "Debian GNU/Linux 13 (trixie)"
    assert resultat["machines"][0]["version_os"] == "13"
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


def test_rechercher_cve_reponse_nvd_valide():
    from labpilot.tools import rechercher_cve

    donnees = {
        "vulnerabilities": [
            {
                "cve": {
                    "id": "CVE-2025-12345",
                    "descriptions": [
                        {"lang": "en", "value": "Example vulnerability"}
                    ],
                    "metrics": {
                        "cvssMetricV31": [
                            {"cvssData": {"baseScore": 8.1}}
                        ]
                    },
                    "published": "2025-01-01T00:00:00.000",
                    "lastModified": "2025-01-02T00:00:00.000",
                    "references": [{"url": "https://example.com/advisory"}],
                }
            }
        ]
    }

    with patch("labpilot.tools.urllib.request.urlopen") as urlopen:
        reponse = urlopen.return_value.__enter__.return_value
        reponse.read.return_value = json.dumps(donnees).encode("utf-8")

        resultat = rechercher_cve("OpenSSH", "9.8")

    assert resultat["disponible"] is True
    assert resultat["source"] == "NVD"
    assert resultat["nombre_resultats"] == 1
    assert resultat["cve"][0]["id"] == "CVE-2025-12345"
    assert resultat["cve"][0]["score_cvss"] == 8.1
    assert resultat["cve"][0]["applicabilite"] == "a_verifier"
    urlopen.assert_called_once()
    assert urlopen.call_args.kwargs["timeout"] == 10


@pytest.mark.parametrize(
    ("produit", "version", "limite"),
    [
        ("", "9.8", 20),
        ("OpenSSH", "", 20),
        ("OpenSSH", "9.8", 0),
        ("OpenSSH", "9.8", 21),
        ("OpenSSH", "9.8", True),
    ],
)

def test_rechercher_cve_rejette_parametres_invalides(
    produit, version, limite
):
    from labpilot.tools import rechercher_cve

    with patch("labpilot.tools.urllib.request.urlopen") as urlopen:
        with pytest.raises(ValueError):
            rechercher_cve(produit, version, limite)

    urlopen.assert_not_called()


def test_rechercher_cve_erreur_reseau():
    from urllib.error import URLError
    from labpilot.tools import rechercher_cve

    with patch(
        "labpilot.tools.urllib.request.urlopen",
        side_effect=URLError("erreur réseau fictive"),
    ):
        resultat = rechercher_cve("OpenSSH", "9.8")

    assert resultat == {
        "disponible": False,
        "erreur": "erreur_reseau",
        "cve": [],
    }

@pytest.mark.parametrize(
    "donnees",
    [
        [],
        {"vulnerabilities": [None]},
        {"vulnerabilities": [{"cve": None}]},
        {"vulnerabilities": [{"cve": {"id": "CVE-2025-12345", "descriptions": [None]}}]},
        {"vulnerabilities": [{"cve": {"id": "CVE-2025-12345", "metrics": None}}]},
        {"vulnerabilities": [{"cve": {"id": "CVE-2025-12345", "references": [None]}}]},
    ],
)
def test_rechercher_cve_reponse_nvd_malformee(donnees):
    from labpilot.tools import rechercher_cve

    with patch("labpilot.tools.urllib.request.urlopen") as urlopen:
        reponse = urlopen.return_value.__enter__.return_value
        reponse.read.return_value = json.dumps(donnees).encode("utf-8")

        resultat = rechercher_cve("OpenSSH", "9.8")

    assert resultat["disponible"] is False
    assert resultat["erreur"] == "reponse_json_invalide"
    assert resultat["cve"] == []


def test_audit_cve_proxmox_rejette_inventaire_mal_forme(monkeypatch):
    monkeypatch.setattr(
        "labpilot.tools.inventaire_os_proxmox",
        lambda: {"disponible": True, "machines": [None]},
    )

    resultat = audit_cve_proxmox()

    assert resultat["disponible"] is False
    assert resultat["erreur"] == "inventaire_proxmox_invalide"
    assert resultat["machines"] == []


def test_audit_cve_proxmox_rejette_reponse_cve_mal_formee(monkeypatch):
    monkeypatch.setattr(
        "labpilot.tools.inventaire_os_proxmox",
        lambda: {
            "disponible": True,
            "machines": [
                {
                    "vmid": 101,
                    "nom": "ubuntu-test",
                    "etat_collecte": "collecte_ok",
                    "nom_os": "Ubuntu",
                    "version_id_os": "24.04",
                }
            ],
        },
    )
    monkeypatch.setattr(
        "labpilot.tools.rechercher_cve",
        lambda **kwargs: {"disponible": True, "cve": "format-invalide"},
    )

    resultat = audit_cve_proxmox()

    assert resultat["disponible"] is True
    assert resultat["nombre_machines_auditees"] == 0
    assert resultat["machines"][0]["etat_audit_cve"] == "erreur_recherche_cve"
    assert resultat["machines"][0]["erreur_cve"] == "reponse_invalide"
    normalise = resultat["machines"][0]["resultat_cve_normalise"]
    assert normalise["disponible"] is False
    assert normalise["erreur"] == "reponse_invalide"
    assert normalise["produit"] == "Ubuntu"
    assert normalise["version_detectee"] == "24.04"
    assert normalise["resultats"] == []


def test_audit_cve_proxmox_recherche_cve_pour_os_identifie():
    with (
        patch(
            "labpilot.tools.inventaire_os_proxmox",
            return_value={
                "disponible": True,
                "nombre_vm_qemu_en_fonctionnement": 1,
                "nombre_os_identifies": 1,
                "machines": [
                    {
                        "vmid": 100,
                        "nom": "vm-ubuntu",
                        "noeud": "pve",
                        "etat_collecte": "collecte_ok",
                        "nom_os": "Ubuntu",
                        "version_os": "Ubuntu 24.04.3 LTS",
                        "version_id_os": "24.04",
                        "noyau": "6.8.0",
                    }
                ],
            },
        ),
        patch(
            "labpilot.tools.rechercher_cve",
            return_value={
                "disponible": True,
                "source": "NVD",
                "nombre_resultats": 1,
                "cve": [
                    {
                        "id": "CVE-2025-12345",
                        "applicabilite": "a_verifier",
                    }
                ],
            },
        ) as rechercher_cve_mock,
    ):
        resultat = audit_cve_proxmox()

    rechercher_cve_mock.assert_called_once_with(
        produit="Ubuntu",
        version="24.04",
        limite=20,
    )
    assert resultat["disponible"] is True
    assert len(resultat["machines"]) == 1
    assert resultat["machines"][0]["vmid"] == 100
    assert resultat["machines"][0]["cve"][0]["id"] == "CVE-2025-12345"
    machine = resultat["machines"][0]
    assert machine["source_cve"] == "NVD"
    assert machine["etat_audit_cve"] == "terminee"

    normalise = machine["resultat_cve_normalise"]
    assert normalise["disponible"] is True
    assert normalise["produit"] == "Ubuntu"
    assert normalise["version_detectee"] == "24.04"
    assert normalise["source"] == "NVD"
    assert normalise["resultats"][0]["identifiant"] == "CVE-2025-12345"
    assert normalise["resultats"][0]["statut"] == "candidate"
    assert normalise["resultats"][0]["versions_affectees"] == []


def test_audit_cve_proxmox_continue_apres_erreur_nvd():
    inventaire = {
        "disponible": True,
        "nombre_vm_qemu_en_fonctionnement": 2,
        "nombre_os_identifies": 2,
        "machines": [
            {
                "vmid": 100,
                "nom": "vm-ubuntu",
                "noeud": "pve",
                "etat_collecte": "collecte_ok",
                "nom_os": "Ubuntu",
                "version_os": "Ubuntu 24.04 LTS",
                "version_id_os": "24.04",
                "noyau": "6.8.0",
            },
            {
                "vmid": 101,
                "nom": "vm-debian",
                "noeud": "pve",
                "etat_collecte": "collecte_ok",
                "nom_os": "Debian GNU/Linux",
                "version_os": "Debian GNU/Linux 12",
                "version_id_os": "12",
                "noyau": "6.1.0",
            },
        ],
    }

    with (
        patch(
            "labpilot.tools.inventaire_os_proxmox",
            return_value=inventaire,
        ),
        patch(
            "labpilot.tools.rechercher_cve",
            side_effect=[
                RuntimeError("NVD indisponible"),
                {
                    "disponible": True,
                    "source": "NVD",
                    "nombre_resultats": 1,
                    "cve": [
                        {
                            "id": "CVE-2025-12345",
                            "applicabilite": "a_verifier",
                        }
                    ],
                    "avertissement": "Applicabilité à vérifier.",
                },
            ],
        ) as rechercher_cve_mock,
    ):
        resultat = audit_cve_proxmox()

    assert rechercher_cve_mock.call_count == 2
    assert resultat["disponible"] is True
    assert resultat["nombre_machines_auditees"] == 1
    assert resultat["machines"][0]["etat_audit_cve"] == "erreur_recherche_cve"
    assert resultat["machines"][1]["etat_audit_cve"] == "terminee"
    assert resultat["machines"][1]["cve"][0]["id"] == "CVE-2025-12345"
    normalise_erreur = resultat["machines"][0]["resultat_cve_normalise"]
    assert normalise_erreur["disponible"] is False
    assert normalise_erreur["erreur"] == "erreur_recherche_cve"
    assert normalise_erreur["resultats"] == []
    assert normalise_erreur["produit"] == "Ubuntu"
    assert normalise_erreur["version_detectee"] == "24.04"

    normalise = resultat["machines"][1]["resultat_cve_normalise"]
    assert normalise["disponible"] is True
    assert normalise["resultats"][0]["identifiant"] == "CVE-2025-12345"
    assert normalise["resultats"][0]["statut"] == "candidate"


def test_audit_cve_proxmox_gere_indisponibilite_proxmox():
    with patch(
        "labpilot.tools.inventaire_os_proxmox",
        side_effect=RuntimeError("Proxmox inaccessible"),
    ):
        resultat = audit_cve_proxmox()

    assert resultat["disponible"] is False
    assert resultat["erreur"] == "inventaire_proxmox_indisponible"
    assert resultat["machines"] == []


def test_audit_cve_proxmox_rejette_limite_invalide():
    with patch("labpilot.tools.inventaire_os_proxmox") as inventaire_mock:
        resultat = audit_cve_proxmox(limite_par_machine=0)

    assert resultat["disponible"] is False
    assert resultat["erreur"] == "limite_par_machine_invalide"
    assert resultat["machines"] == []
    inventaire_mock.assert_not_called()


def test_audit_cve_proxmox_ignore_os_non_identifie():
    inventaire = {
        "disponible": True,
        "nombre_vm_qemu_en_fonctionnement": 1,
        "nombre_os_identifies": 0,
        "machines": [
            {
                "vmid": 102,
                "nom": "vm-inconnue",
                "noeud": "pve",
                "etat_collecte": "os_inconnu",
                "nom_os": None,
                "version_os": None,
                "version_id_os": None,
                "noyau": None,
            }
        ],
    }

    with (
        patch(
            "labpilot.tools.inventaire_os_proxmox",
            return_value=inventaire,
        ),
        patch("labpilot.tools.rechercher_cve") as rechercher_cve_mock,
    ):
        resultat = audit_cve_proxmox()

    rechercher_cve_mock.assert_not_called()
    assert resultat["disponible"] is True
    assert resultat["nombre_machines"] == 1
    assert resultat["nombre_machines_auditees"] == 0
    assert resultat["machines"][0]["vmid"] == 102
    assert resultat["machines"][0]["etat_audit_cve"] == "ignoree_os_non_identifie"
    assert resultat["machines"][0]["cve"] == []


def test_audit_cve_proxmox_est_enregistre_comme_outil():
    assert OUTILS["audit_cve_proxmox"] is audit_cve_proxmox

    definitions = [
        definition["function"]
        for definition in DEFINITIONS_OUTILS
        if definition.get("function", {}).get("name") == "audit_cve_proxmox"
    ]

    assert len(definitions) == 1
    assert "limite_par_machine" in definitions[0]["parameters"]["properties"]


def test_audit_cve_proxmox_ignore_truenas_sans_version_produit():
    with (
        patch(
            "labpilot.tools.inventaire_os_proxmox",
            return_value={
                "disponible": True,
                "machines": [
                    {
                        "vmid": 400,
                        "nom": "truenas",
                        "etat_collecte": "collecte_ok",
                        "nom_os": "Debian GNU/Linux",
                        "version_os": "Debian GNU/Linux 12",
                        "version_id_os": "12",
                        "noyau": "6.12.105-production+truenas",
                    }
                ],
            },
        ),
        patch("labpilot.tools.rechercher_cve") as rechercher_cve_mock,
    ):
        resultat = audit_cve_proxmox()

    machine = resultat["machines"][0]
    rechercher_cve_mock.assert_not_called()
    assert machine["produit_cve"] == "TrueNAS"
    assert machine["etat_audit_cve"] == "ignoree_version_produit_inconnue"
    assert "Debian" in machine["motif_audit_cve"]
    assert machine["cve"] == []
    assert machine["resultat_cve_normalise"] is None


def test_audit_cve_proxmox_ignore_home_assistant_os_sans_source_dediee():
    with (
        patch(
            "labpilot.tools.inventaire_os_proxmox",
            return_value={
                "disponible": True,
                "machines": [
                    {
                        "vmid": 300,
                        "nom": "haos18-2",
                        "etat_collecte": "collecte_ok",
                        "nom_os": "Home Assistant OS 18.2",
                        "version_os": "18.2",
                        "version_id_os": "18.2",
                        "noyau": "6.18.39-haos",
                    }
                ],
            },
        ),
        patch("labpilot.tools.rechercher_cve") as rechercher_cve_mock,
    ):
        resultat = audit_cve_proxmox()

    machine = resultat["machines"][0]
    rechercher_cve_mock.assert_not_called()
    assert machine["produit_cve"] == "Home Assistant OS"
    assert machine["version_produit_cve"] == "18.2"
    assert machine["etat_audit_cve"] == "ignoree_source_produit_non_integree"
    assert machine["cve"] == []
    assert machine["resultat_cve_normalise"] is None


def test_statuts_cve_autorises():
    from labpilot.tools import STATUTS_CVE_AUTORISES

    assert STATUTS_CVE_AUTORISES == {
        "candidate",
        "potentiellement_affectee",
        "affectee_confirmee",
        "non_affectee",
        "correctif_disponible",
        "verification_incomplete",
    }


def test_valider_resultat_connecteur_cve_accepte_resultat_valide():
    from labpilot.tools import valider_resultat_connecteur_cve

    resultat = {
        "produit": "Nextcloud",
        "version_detectee": "35.0.2",
        "source": "avis_securite_fournisseur",
        "disponible": True,
        "erreur": None,
        "resultats": [
            {
                "identifiant": "CVE-2025-12345",
                "versions_affectees": ["35.0.0 à 35.0.2"],
                "version_corrigee": "35.0.3",
                "statut": "candidate",
                "preuve": ["https://example.com/advisory"],
                "date_verification": "2026-10-26",
            }
        ],
    }

    assert valider_resultat_connecteur_cve(resultat) is True

@pytest.mark.parametrize(
    "modification",
    [
        {"produit": ""},
        {"disponible": "oui"},
        {"resultats": "aucun"},
        {"resultats": None},
        {
            "resultats": [
                {
                    "identifiant": "CVE-2025-12345",
                    "versions_affectees": [],
                    "version_corrigee": None,
                    "statut": "statut_inconnu",
                    "preuve": [],
                    "date_verification": None,
                }
            ]
        },
        {"source": ""},
        {"erreur": 123},
        {
            "resultats": [
                {
                    "identifiant": "CVE-2025-12345",
                    "versions_affectees": [],
                    "version_corrigee": None,
                    "statut": None,
                    "preuve": [],
                    "date_verification": None,
                }
            ]
        },
        {
            "resultats": [
                {
                    "identifiant": "CVE-2025-12345",
                    "versions_affectees": [],
                    "version_corrigee": None,
                    "statut": "candidate",
                    "preuve": [],
                }
            ]
        },
    ],
)
def test_valider_resultat_connecteur_cve_rejette_resultat_invalide(
    modification,
):
    from labpilot.tools import valider_resultat_connecteur_cve

    resultat = {
        "produit": "Nextcloud",
        "version_detectee": "35.0.2",
        "source": "avis_securite_fournisseur",
        "disponible": True,
        "erreur": None,
        "resultats": [],
    }
    resultat.update(modification)

    assert valider_resultat_connecteur_cve(resultat) is False

def test_valider_resultat_connecteur_cve_accepte_source_indisponible():
    from labpilot.tools import valider_resultat_connecteur_cve

    resultat = {
        "produit": "Debian",
        "version_detectee": "13",
        "source": "avis_securite_debian",
        "disponible": False,
        "erreur": "erreur_reseau",
        "resultats": [],
    }

    assert valider_resultat_connecteur_cve(resultat) is True



def test_adapter_resultat_nvd_cve_conserve_les_cve_comme_candidates():
    from labpilot.tools import adapter_resultat_nvd_cve

    resultat_nvd = {
        "disponible": True,
        "cve": [
            {
                "id": "CVE-2026-12345",
                "references": ["https://example.org/advisory"],
            }
        ],
    }

    resultat = adapter_resultat_nvd_cve(
        resultat_nvd,
        "Nextcloud",
        "35.0.2",
    )

    assert resultat["disponible"] is True
    assert resultat["erreur"] is None
    assert resultat["produit"] == "Nextcloud"
    assert resultat["version_detectee"] == "35.0.2"
    assert resultat["source"] == "NVD"
    assert resultat["resultats"][0]["identifiant"] == "CVE-2026-12345"
    assert resultat["resultats"][0]["statut"] == "candidate"
    assert resultat["resultats"][0]["versions_affectees"] == []
    assert resultat["resultats"][0]["version_corrigee"] is None
    assert resultat["resultats"][0]["preuve"] == [
        "https://example.org/advisory"
    ]


def test_adapter_resultat_nvd_cve_gere_une_source_indisponible():
    from labpilot.tools import adapter_resultat_nvd_cve

    resultat = adapter_resultat_nvd_cve(
        {
            "disponible": False,
            "erreur": "erreur_reseau",
            "cve": [],
        },
        "Debian",
        "13",
    )

    assert resultat["disponible"] is False
    assert resultat["erreur"] == "erreur_reseau"
    assert resultat["resultats"] == []


def test_adapter_resultat_nvd_cve_normalise_erreur_absente():
    from labpilot.tools import (
        adapter_resultat_nvd_cve,
        valider_resultat_connecteur_cve,
    )

    resultat = adapter_resultat_nvd_cve(
        {
            "disponible": False,
            "erreur": "",
            "cve": [],
        },
        "Debian",
        "13",
    )

    assert resultat["disponible"] is False
    assert resultat["erreur"] == "source_indisponible"
    assert resultat["resultats"] == []
    assert valider_resultat_connecteur_cve(resultat) is True


def test_adapter_resultat_nvd_cve_reponse_mal_formee():
    from labpilot.tools import (
        adapter_resultat_nvd_cve,
        valider_resultat_connecteur_cve,
    )

    resultat = adapter_resultat_nvd_cve(
        {"disponible": True, "cve": "format_invalide"},
        "Debian",
        "13",
    )

    assert resultat["disponible"] is False
    assert resultat["erreur"] == "reponse_invalide"
    assert resultat["resultats"] == []
    assert valider_resultat_connecteur_cve(resultat) is True


def test_adapter_resultat_nvd_cve_produit_vide():
    from labpilot.tools import (
        adapter_resultat_nvd_cve,
        valider_resultat_connecteur_cve,
    )

    resultat = adapter_resultat_nvd_cve(
        {"disponible": False, "erreur": "erreur_reseau"},
        "",
        "13",
    )

    assert resultat["disponible"] is False
    assert resultat["erreur"] == "erreur_reseau"
    assert resultat["produit"] == "inconnu"
    assert valider_resultat_connecteur_cve(resultat) is True


def test_adapter_resultat_nvd_cve_erreur_respecte_le_contrat():
    from labpilot.tools import (
        adapter_resultat_nvd_cve,
        valider_resultat_connecteur_cve,
    )

    resultat = adapter_resultat_nvd_cve(
        {"disponible": False, "erreur": "erreur_reseau"},
        "Debian",
        "13",
    )

    assert resultat["disponible"] is False
    assert resultat["erreur"] == "erreur_reseau"
    assert resultat["resultats"] == []
    assert valider_resultat_connecteur_cve(resultat) is True


def test_finaliser_resultat_connecteur_cve_champs_invalides():
    from labpilot.tools import (
        finaliser_resultat_connecteur_cve,
        valider_resultat_connecteur_cve,
    )

    resultat = finaliser_resultat_connecteur_cve({
        "produit": None,
        "version_detectee": 13,
        "source": [],
        "disponible": False,
        "erreur": "reponse_invalide",
        "resultats": [],
    })

    assert resultat["disponible"] is False
    assert resultat["erreur"] == "contrat_invalide"
    assert valider_resultat_connecteur_cve(resultat) is True


def test_audit_cve_proxmox_normalise_erreur_nvd_non_textuelle():
    from unittest.mock import patch

    inventaire = {
        "disponible": True,
        "machines": [
            {
                "vmid": 101,
                "nom": "ubuntu-test",
                "etat_collecte": "collecte_ok",
                "nom_os": "Ubuntu",
                "version_id_os": "24.04",
            }
        ],
    }

    with (
        patch(
            "labpilot.tools.inventaire_os_proxmox",
            return_value=inventaire,
        ),
        patch(
            "labpilot.tools.rechercher_cve",
            return_value={
                "disponible": False,
                "erreur": 123,
            },
        ),
    ):
        resultat = audit_cve_proxmox()

    machine = resultat["machines"][0]
    assert machine["erreur_cve"] == "reponse_indisponible"
    assert (
        machine["resultat_cve_normalise"]["erreur"]
        == "reponse_indisponible"
    )
