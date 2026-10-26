import json
from unittest.mock import MagicMock, patch

import pytest

from labpilot.proxmox_guest_agent import (
    ErreurCollectePaquetsDebian,
    inventaire_paquets_debian_proxmox,
)


SORTIE_DPKG = (
    "openssh-server\t1:9.2p1-2+deb12u7\topenssh\t1:9.2p1-2+deb12u7\n"
    "libc6:amd64\t2.36-9+deb12u10\tglibc\t2.36-9+deb12u10\n"
)


def reponse_json(donnees):
    reponse = MagicMock()
    reponse.__enter__.return_value = reponse
    reponse.__exit__.return_value = False
    reponse.read.return_value = json.dumps({"data": donnees}).encode()
    reponse.__iter__.return_value = iter([])
    reponse.headers = {}
    reponse.read.return_value = json.dumps({"data": donnees}).encode()
    reponse.__enter__.return_value.__class__ = MagicMock
    return reponse


def reponse_json_load(donnees):
    reponse = MagicMock()
    reponse.__enter__.return_value = reponse
    reponse.__exit__.return_value = False
    reponse.read.return_value = json.dumps({"data": donnees}).encode()
    return reponse


@patch("labpilot.proxmox_guest_agent.ssl.create_default_context")
@patch("labpilot.proxmox_guest_agent.urllib.request.urlopen")
@patch("labpilot.proxmox_guest_agent.time.sleep")
def test_collecte_reussie(mock_sleep, mock_urlopen, mock_tls):
    demarrage = reponse_json_load({"pid": 123})
    termine = reponse_json_load({
        "exited": 1,
        "exitcode": 0,
        "out-truncated": 0,
        "out-data": SORTIE_DPKG,
    })
    mock_urlopen.side_effect = [demarrage, termine]

    with (
        patch("labpilot.proxmox_guest_agent.PROXMOX_URL", "https://pve.example:8006"),
        patch("labpilot.proxmox_guest_agent.PROXMOX_TOKEN_ID", "labpilot@pve!readonly"),
        patch("labpilot.proxmox_guest_agent.PROXMOX_TOKEN_SECRET", "secret"),
        patch("labpilot.proxmox_guest_agent.PROXMOX_CA_FILE", "/tmp/ca.pem"),
    ):
        paquets = inventaire_paquets_debian_proxmox("maltas", 401)

    assert len(paquets) == 2
    assert paquets[0]["nom"] == "openssh-server"
    assert paquets[1]["paquet_source"] == "glibc"
    assert mock_urlopen.call_count == 2


@pytest.mark.parametrize("vmid", [0, -1, True, "401", None])
def test_refuse_vmid_invalide(vmid):
    with pytest.raises(ValueError):
        inventaire_paquets_debian_proxmox("maltas", vmid)


@pytest.mark.parametrize("noeud", ["", "../root", "mal tas", "nœud"])
def test_refuse_noeud_invalide(noeud):
    with pytest.raises(ValueError):
        inventaire_paquets_debian_proxmox(noeud, 401)


@patch("labpilot.proxmox_guest_agent.ssl.create_default_context")
@patch("labpilot.proxmox_guest_agent.urllib.request.urlopen")
def test_refuse_code_retour_non_nul(mock_urlopen, mock_tls):
    mock_urlopen.return_value = reponse_json_load({"pid": 123})
    mock_urlopen.side_effect = [
        reponse_json_load({"pid": 123}),
        reponse_json_load({
            "exited": 1,
            "exitcode": 1,
            "out-truncated": 0,
            "out-data": "",
        }),
    ]

    with (
        patch("labpilot.proxmox_guest_agent.PROXMOX_URL", "https://pve.example:8006"),
        patch("labpilot.proxmox_guest_agent.PROXMOX_TOKEN_ID", "labpilot@pve!readonly"),
        patch("labpilot.proxmox_guest_agent.PROXMOX_TOKEN_SECRET", "secret"),
        patch("labpilot.proxmox_guest_agent.PROXMOX_CA_FILE", "/tmp/ca.pem"),
    ):
        with pytest.raises(ErreurCollectePaquetsDebian, match="a échoué"):
            inventaire_paquets_debian_proxmox("maltas", 401)


@patch("labpilot.proxmox_guest_agent.ssl.create_default_context")
@patch("labpilot.proxmox_guest_agent.urllib.request.urlopen")
def test_refuse_sortie_tronquee(mock_urlopen, mock_tls):
    mock_urlopen.side_effect = [
        reponse_json_load({"pid": 123}),
        reponse_json_load({
            "exited": 1,
            "exitcode": 0,
            "out-truncated": 1,
            "out-data": SORTIE_DPKG,
        }),
    ]

    with (
        patch("labpilot.proxmox_guest_agent.PROXMOX_URL", "https://pve.example:8006"),
        patch("labpilot.proxmox_guest_agent.PROXMOX_TOKEN_ID", "labpilot@pve!readonly"),
        patch("labpilot.proxmox_guest_agent.PROXMOX_TOKEN_SECRET", "secret"),
        patch("labpilot.proxmox_guest_agent.PROXMOX_CA_FILE", "/tmp/ca.pem"),
    ):
        with pytest.raises(ErreurCollectePaquetsDebian, match="tronqué"):
            inventaire_paquets_debian_proxmox("maltas", 401)
