"""Collecte en lecture seule des paquets Debian via le QEMU Guest Agent."""

import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

from labpilot.configuration import (
    PROXMOX_URL,
    PROXMOX_TOKEN_ID,
    PROXMOX_TOKEN_SECRET,
)
PROXMOX_CA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "certs",
    "proxmox-root-ca.pem",
)
from labpilot.debian_security import (
    ErreurInventairePaquetsDebian,
    normaliser_inventaire_paquets_debian,
)


class ErreurCollectePaquetsDebian(Exception):
    """Erreur de collecte de paquets Debian via Proxmox."""


def inventaire_paquets_debian_proxmox(
    noeud: str,
    vmid: int,
    delai_maximal: int = 30,
    intervalle_interrogation: float = 0.5,
) -> list[dict]:
    """Collecte les paquets Debian installés sur une VM QEMU en lecture seule."""
    if (
        not isinstance(noeud, str)
        or not noeud
        or any(
            not (c.isascii() and (c.isalnum() or c in "_.-"))
            for c in noeud
        )
    ):
        raise ValueError("Nom de nœud Proxmox invalide.")

    if isinstance(vmid, bool) or not isinstance(vmid, int) or vmid <= 0:
        raise ValueError("Identifiant VM invalide.")

    if (
        isinstance(delai_maximal, bool)
        or not isinstance(delai_maximal, int)
        or not 1 <= delai_maximal <= 120
    ):
        raise ValueError("Le délai maximal doit être compris entre 1 et 120 secondes.")

    if (
        isinstance(intervalle_interrogation, bool)
        or not isinstance(intervalle_interrogation, (int, float))
        or not 0.1 <= intervalle_interrogation <= 5
    ):
        raise ValueError("Intervalle d'interrogation invalide.")

    if not all((PROXMOX_URL, PROXMOX_TOKEN_ID, PROXMOX_TOKEN_SECRET)):
        raise ErreurCollectePaquetsDebian("Configuration Proxmox absente.")

    try:
        contexte_tls = ssl.create_default_context(cafile=PROXMOX_CA_FILE)
    except Exception:
        raise ErreurCollectePaquetsDebian(
            "Impossible de charger le certificat CA Proxmox."
        ) from None

    base_url = PROXMOX_URL.rstrip("/")
    en_tetes = {
        "Authorization": (
            f"PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_TOKEN_SECRET}"
        ),
        "Accept": "application/json",
    }
    chemin_base = f"/api2/json/nodes/{noeud}/qemu/{vmid}/agent"

    def appeler_api(chemin: str, parametres=None, methode="GET") -> dict:
        url = f"{base_url}{chemin}"
        donnees = None

        if parametres:
            if methode == "GET":
                url += "?" + urllib.parse.urlencode(parametres)
            else:
                donnees = urllib.parse.urlencode(parametres).encode("utf-8")

        requete = urllib.request.Request(
            url,
            data=donnees,
            headers=en_tetes,
            method=methode,
        )

        try:
            with urllib.request.urlopen(
                requete, timeout=10, context=contexte_tls
            ) as reponse:
                contenu = json.load(reponse)
        except urllib.error.HTTPError as erreur:
            raise ErreurCollectePaquetsDebian(
                f"Erreur HTTP Proxmox : {erreur.code}."
            ) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise ErreurCollectePaquetsDebian(
                "API Proxmox ou QEMU Guest Agent indisponible."
            ) from None
        except (ValueError, json.JSONDecodeError):
            raise ErreurCollectePaquetsDebian(
                "Réponse JSON Proxmox invalide."
            ) from None

        if not isinstance(contenu, dict) or "data" not in contenu:
            raise ErreurCollectePaquetsDebian(
                "Structure de réponse Proxmox invalide."
            )

        return contenu["data"]

    format_paquet = (
        "${binary:Package}\\t${Version}\\t"
        "${source:Package}\\t${source:Version}\\n"
    )
    resultat = appeler_api(
        f"{chemin_base}/exec",
        [
            ("command", "/usr/bin/dpkg-query"),
            ("command", "-W"),
            ("command", f"-f={format_paquet}"),
        ],
        methode="POST",
    )

    if not isinstance(resultat, dict):
        raise ErreurCollectePaquetsDebian(
            "Réponse d'exécution du Guest Agent invalide."
        )

    pid = resultat.get("pid")
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        raise ErreurCollectePaquetsDebian(
            "Le Guest Agent n'a pas fourni de PID valide."
        )

    echeance = time.monotonic() + delai_maximal

    while time.monotonic() < echeance:
        statut = appeler_api(
            f"{chemin_base}/exec-status",
            {"pid": pid},
        )

        if not isinstance(statut, dict):
            raise ErreurCollectePaquetsDebian(
                "Statut d'exécution du Guest Agent invalide."
            )

        if statut.get("exited"):
            if statut.get("out-truncated"):
                raise ErreurCollectePaquetsDebian(
                    "Inventaire tronqué par le Guest Agent."
                )

            code_retour = statut.get("exitcode")
            if code_retour != 0:
                raise ErreurCollectePaquetsDebian(
                    f"dpkg-query a échoué (code {code_retour!r})."
                )

            sortie = statut.get("out-data")
            try:
                return normaliser_inventaire_paquets_debian(sortie)
            except ErreurInventairePaquetsDebian as erreur:
                raise ErreurCollectePaquetsDebian(
                    f"Inventaire Debian invalide : {erreur}"
                ) from None

        time.sleep(min(intervalle_interrogation, max(0, echeance - time.monotonic())))

    raise ErreurCollectePaquetsDebian(
        "Délai maximal dépassé pendant la collecte des paquets."
    )
