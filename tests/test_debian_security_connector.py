import pytest

from labpilot.debian_security_connector import (
    auditer_paquets_debian_proxmox,
)


def test_refuse_distribution_debian_non_prise_en_charge():
    resultat = auditer_paquets_debian_proxmox(
        "maltas",
        401,
        "sid",
    )

    assert resultat["disponible"] is False
    assert resultat["erreur"] == "distribution_debian_non_prise_en_charge"
    assert resultat["resultats"] == []


def test_source_indisponible(monkeypatch):
    import labpilot.debian_security_connector as connecteur

    def collecte_indisponible(*args, **kwargs):
        raise connecteur.ErreurCollectePaquetsDebian("détail interne")

    monkeypatch.setattr(
        connecteur,
        "inventaire_paquets_debian_proxmox",
        collecte_indisponible,
    )

    resultat = auditer_paquets_debian_proxmox(
        "maltas",
        401,
        "13",
    )

    assert resultat["disponible"] is False
    assert resultat["erreur"] == "source_securite_indisponible"
    assert resultat["resultats"] == []


def test_rapprochement_debian_conserve_statut_prudent(monkeypatch):
    import labpilot.debian_security_connector as connecteur

    monkeypatch.setattr(
        connecteur,
        "inventaire_paquets_debian_proxmox",
        lambda *args, **kwargs: [
            {
                "nom": "exemple",
                "version": "1.0-1",
                "paquet_source": "exemple",
                "version_source": "1.0-1",
            }
        ],
    )
    monkeypatch.setattr(
        connecteur,
        "charger_avis_debian",
        lambda: {
            "exemple": {
                "CVE-2025-12345": {
                    "description": "CVE de test",
                    "releases": {
                        "trixie": {
                            "status": "open",
                            "fixed_version": None,
                            "urgency": "high",
                        }
                    },
                }
            }
        },
    )

    resultat = auditer_paquets_debian_proxmox(
        "maltas",
        401,
        "13",
    )

    assert resultat["disponible"] is True
    assert resultat["erreur"] is None
    assert len(resultat["resultats"]) == 1
    assert resultat["resultats"][0]["identifiant"] == "CVE-2025-12345"
    assert resultat["resultats"][0]["statut"] == "potentiellement_affectee"
    assert resultat["resultats"][0]["date_verification"]


def test_dedoublonne_paquets_binaires_de_meme_source_et_version(monkeypatch):
    import labpilot.debian_security_connector as connecteur

    monkeypatch.setattr(
        connecteur,
        "inventaire_paquets_debian_proxmox",
        lambda *args, **kwargs: [
            {
                "nom": "exemple",
                "version": "1.0-1",
                "paquet_source": "exemple",
                "version_source": "1.0-1",
            },
            {
                "nom": "exemple-data",
                "version": "1.0-1",
                "paquet_source": "exemple",
                "version_source": "1.0-1",
            },
        ],
    )
    monkeypatch.setattr(
        connecteur,
        "charger_avis_debian",
        lambda: {
            "exemple": {
                "CVE-2025-12345": {
                    "description": "CVE de test",
                    "releases": {
                        "trixie": {
                            "status": "open",
                            "fixed_version": None,
                            "urgency": "high",
                        }
                    },
                }
            }
        },
    )

    resultat = auditer_paquets_debian_proxmox("maltas", 401, "13")

    assert resultat["disponible"] is True
    assert len(resultat["resultats"]) == 1
    assert resultat["resultats"][0]["identifiant"] == "CVE-2025-12345"
    assert resultat["resultats"][0]["statut"] == "potentiellement_affectee"
