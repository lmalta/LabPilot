from labpilot.debian_security import normaliser_avis_debian


def test_normaliser_avis_debian_correctif_disponible():
    avis = {
        "exemple-paquet": {
            "CVE-2025-12345": {
                "description": "Vulnérabilité de test",
                "scope": "local",
                "releases": {
                    "bookworm": {
                        "status": "resolved",
                        "repositories": {
                            "bookworm": "1.2.4-1"
                        },
                        "fixed_version": "1.2.4-1",
                        "urgency": "high",
                    }
                },
            }
        }
    }

    resultat = normaliser_avis_debian(avis, "bookworm")

    assert len(resultat) == 1
    assert resultat[0]["identifiant"] == "CVE-2025-12345"
    assert resultat[0]["paquet_source"] == "exemple-paquet"
    assert resultat[0]["statut"] == "correctif_disponible"
    assert resultat[0]["version_corrigee"] == "1.2.4-1"


def test_normaliser_avis_debian_version_zero_non_affectee():
    avis = {
        "exemple-paquet": {
            "CVE-2025-12345": {
                "description": "CVE non applicable au paquet source",
                "releases": {
                    "bookworm": {
                        "status": "resolved",
                        "fixed_version": "0",
                        "urgency": "unimportant",
                    }
                },
            }
        }
    }

    resultat = normaliser_avis_debian(avis, "bookworm")

    assert resultat[0]["statut"] == "non_affectee"
    assert resultat[0]["version_corrigee"] is None


def test_normaliser_avis_debian_statut_indetermine():
    avis = {
        "exemple-paquet": {
            "CVE-2025-12345": {
                "releases": {
                    "bookworm": {
                        "status": "undetermined",
                    }
                }
            }
        }
    }

    resultat = normaliser_avis_debian(avis, "bookworm")

    assert resultat[0]["statut"] == "verification_incomplete"


def test_normaliser_avis_debian_ignore_autres_distributions():
    avis = {
        "exemple-paquet": {
            "CVE-2025-12345": {
                "releases": {
                    "trixie": {
                        "status": "open",
                    }
                }
            }
        }
    }

    assert normaliser_avis_debian(avis, "bookworm") == []


def test_normaliser_avis_debian_reponse_invalide():
    assert normaliser_avis_debian([], "bookworm") == []
    assert normaliser_avis_debian({}, "") == []

import json

import pytest

from labpilot.debian_security import (
    ErreurTrackerDebian,
    charger_avis_debian,
)


def test_charger_avis_debian_reponse_valide(monkeypatch):
    class Reponse:
        headers = {
            "Content-Type": "application/json",
            "Content-Length": "2",
        }

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, taille):
            return b"{}"

    monkeypatch.setattr(
        "labpilot.debian_security.urlopen",
        lambda *args, **kwargs: Reponse(),
    )

    assert charger_avis_debian() == {}


def test_charger_avis_debian_reponse_invalide(monkeypatch):
    class Reponse:
        headers = {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, taille):
            return b"pas du json"

    monkeypatch.setattr(
        "labpilot.debian_security.urlopen",
        lambda *args, **kwargs: Reponse(),
    )

    with pytest.raises(ErreurTrackerDebian):
        charger_avis_debian()


def test_charger_avis_debian_racine_invalide(monkeypatch):
    class Reponse:
        headers = {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, taille):
            return json.dumps([]).encode()

    monkeypatch.setattr(
        "labpilot.debian_security.urlopen",
        lambda *args, **kwargs: Reponse(),
    )

    with pytest.raises(ErreurTrackerDebian):
        charger_avis_debian()


def test_charger_avis_debian_delai_invalide():
    with pytest.raises(ValueError):
        charger_avis_debian(timeout=0)

from labpilot.debian_security import comparer_versions_debian


def test_comparer_versions_debian_revision():
    assert comparer_versions_debian("1.2.3-1", "1.2.3-2") == -1


def test_comparer_versions_debian_suffixe_tilde():
    assert comparer_versions_debian("1.0~rc1-1", "1.0-1") == -1


def test_comparer_versions_debian_epoch():
    assert comparer_versions_debian("2:1.0-1", "1:9.9-9") == 1


def test_comparer_versions_debian_versions_equivalentes():
    assert comparer_versions_debian("1.2.3", "1.2.3-0") == 0
    assert comparer_versions_debian("1.02", "1.2") == 0


def test_comparer_versions_debian_entiers_numeriques():
    assert comparer_versions_debian("1.9", "1.10") == -1


def test_comparer_versions_debian_rejette_versions_vides():
    import pytest

    with pytest.raises(ValueError):
        comparer_versions_debian("", "1.0")

    with pytest.raises(ValueError):
        comparer_versions_debian("1.0", "")


def test_comparer_versions_debian_cas_de_reference():
    cas = [
        ("1.0~rc1", "1.0", -1),
        ("1.0", "1.0-0", 0),
        ("1.0-1", "1.0-2", -1),
        ("1.9", "1.10", -1),
        ("2:1.0-1", "1:9.9-9", 1),
        ("1.0+a", "1.0a", 1),
        ("1.0-1+b", "1.0-1", 1),
        ("1.000", "1.0", 0),
        ("1.0~~", "1.0~", -1),
    ]

    for version_a, version_b, attendu in cas:
        assert comparer_versions_debian(version_a, version_b) == attendu
        assert comparer_versions_debian(version_b, version_a) == -attendu


from labpilot.debian_security import (
    ErreurInventairePaquetsDebian,
    normaliser_inventaire_paquets_debian,
)


def test_normaliser_inventaire_paquets_debian():
    sortie = (
        "openssh-server\t1:9.2p1-2+deb12u7\topenssh\t1:9.2p1-2+deb12u7\n"
        "libc6:amd64\t2.36-9+deb12u10\tglibc\t2.36-9+deb12u10\n"
    )

    paquets = normaliser_inventaire_paquets_debian(sortie)

    assert paquets == [
        {
            "nom": "openssh-server",
            "version": "1:9.2p1-2+deb12u7",
            "paquet_source": "openssh",
            "version_source": "1:9.2p1-2+deb12u7",
        },
        {
            "nom": "libc6:amd64",
            "version": "2.36-9+deb12u10",
            "paquet_source": "glibc",
            "version_source": "2.36-9+deb12u10",
        },
    ]


def test_normaliser_inventaire_paquets_debian_rejette_ligne_invalide():
    with pytest.raises(ErreurInventairePaquetsDebian):
        normaliser_inventaire_paquets_debian(
            "openssh-server\t1.0\topenssh\n"
        )


def test_normaliser_inventaire_paquets_debian_rejette_doublons():
    ligne = "openssh-server\t1.0\topenssh\t1.0\n"

    with pytest.raises(ErreurInventairePaquetsDebian):
        normaliser_inventaire_paquets_debian(ligne + ligne)


def test_normaliser_inventaire_paquets_debian_rejette_sortie_vide():
    with pytest.raises(ErreurInventairePaquetsDebian):
        normaliser_inventaire_paquets_debian("")


def test_rapprochement_debian_devra_reconnaitre_les_statuts():
    """Réserve les cas attendus pour le rapprochement paquet/CVE."""
    from labpilot.debian_security import normaliser_avis_debian

    avis = {
        "exemple-paquet": {
            "CVE-2025-10001": {
                "description": "Correctif publié",
                "releases": {
                    "trixie": {
                        "status": "resolved",
                        "fixed_version": "2.0-2",
                        "repositories": {"trixie": "2.0-2"},
                        "urgency": "high",
                    }
                },
            },
            "CVE-2025-10002": {
                "description": "Paquet non affecté",
                "releases": {
                    "trixie": {
                        "status": "resolved",
                        "fixed_version": "0",
                        "urgency": "unimportant",
                    }
                },
            },
            "CVE-2025-10003": {
                "description": "Analyse incomplète",
                "releases": {
                    "trixie": {"status": "undetermined"},
                },
            },
        }
    }

    resultat = normaliser_avis_debian(avis, "trixie")
    par_cve = {avis["identifiant"]: avis for avis in resultat}

    assert par_cve["CVE-2025-10001"]["statut"] == "correctif_disponible"
    assert par_cve["CVE-2025-10002"]["statut"] == "non_affectee"
    assert par_cve["CVE-2025-10003"]["statut"] == "verification_incomplete"


def test_rapprocher_avis_debian_version_anterieure_au_correctif():
    from labpilot.debian_security import rapprocher_avis_debian_paquet
    from labpilot.security_contracts import valider_resultat_connecteur_cve

    avis = {
        "exemple-paquet": {
            "CVE-2025-10011": {
                "description": "Avis de test",
                "releases": {
                    "trixie": {
                        "status": "resolved",
                        "fixed_version": "2.0-2",
                        "repositories": {"trixie": "2.0-2"},
                        "urgency": "high",
                    }
                },
            }
        }
    }

    resultat = rapprocher_avis_debian_paquet(
        avis, "exemple-paquet", "2.0-1", "trixie"
    )

    assert len(resultat) == 1
    assert resultat[0]["statut"] == "correctif_disponible"
    assert resultat[0]["version_corrigee"] == "2.0-2"
    assert valider_resultat_connecteur_cve({
        "produit": "exemple-paquet",
        "version_detectee": "2.0-1",
        "source": "Debian Security Tracker",
        "disponible": True,
        "erreur": None,
        "resultats": resultat,
    })


def test_rapprocher_avis_debian_version_non_anterieure():
    from labpilot.debian_security import rapprocher_avis_debian_paquet

    avis = {
        "exemple-paquet": {
            "CVE-2025-10012": {
                "description": "Avis de test",
                "releases": {
                    "trixie": {
                        "status": "resolved",
                        "fixed_version": "2.0-2",
                    }
                },
            }
        }
    }

    resultat = rapprocher_avis_debian_paquet(
        avis, "exemple-paquet", "2.0-2", "trixie"
    )

    assert resultat[0]["statut"] == "verification_incomplete"


def test_rapprocher_avis_debian_paquet_absent():
    from labpilot.debian_security import rapprocher_avis_debian_paquet

    assert rapprocher_avis_debian_paquet(
        {}, "paquet-absent", "1.0-1", "trixie"
    ) == []


def test_rapprocher_avis_debian_rejette_version_vide():
    import pytest
    from labpilot.debian_security import rapprocher_avis_debian_paquet

    with pytest.raises(ValueError):
        rapprocher_avis_debian_paquet(
            {}, "exemple-paquet", "", "trixie"
        )


def test_rapprocher_avis_debian_statut_open_reste_prudent():
    from labpilot.debian_security import rapprocher_avis_debian_paquet

    avis = {
        "exemple-paquet": {
            "CVE-2025-10013": {
                "description": "Avis ouvert",
                "releases": {
                    "trixie": {
                        "status": "open",
                        "repositories": {"trixie": "2.0-2"},
                        "urgency": "high",
                    }
                },
            }
        }
    }

    resultat = rapprocher_avis_debian_paquet(
        avis, "exemple-paquet", "2.0-1", "trixie"
    )

    assert len(resultat) == 1
    assert resultat[0]["statut"] == "potentiellement_affectee"
    assert resultat[0]["version_corrigee"] is None


def test_rapprocher_avis_debian_fixed_version_zero():
    from labpilot.debian_security import rapprocher_avis_debian_paquet

    avis = {
        "exemple-paquet": {
            "CVE-2025-10014": {
                "description": "Paquet non affecté",
                "releases": {
                    "trixie": {
                        "status": "resolved",
                        "fixed_version": "0",
                        "urgency": "unimportant",
                    }
                },
            }
        }
    }

    resultat = rapprocher_avis_debian_paquet(
        avis, "exemple-paquet", "2.0-1", "trixie"
    )

    assert len(resultat) == 1
    assert resultat[0]["statut"] == "non_affectee"
    assert resultat[0]["version_corrigee"] is None
    assert any("fixed_version=0" in preuve for preuve in resultat[0]["preuve"])
