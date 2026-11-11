"""Tests du contrat des preuves CVE structurées."""

import pytest

from labpilot.security_contracts import valider_resultat_connecteur_cve


def creer_resultat(statut="candidate", preuves=None):
    return {
        "produit": "Debian",
        "version_detectee": "13",
        "source": "Debian Security Tracker",
        "disponible": True,
        "erreur": None,
        "resultats": [
            {
                "identifiant": "CVE-2026-12345",
                "versions_affectees": [],
                "version_corrigee": None,
                "statut": statut,
                "preuve": ["https://example.org/advisory"],
                "preuves_structurees": preuves or [],
                "date_verification": "2026-11-11",
            }
        ],
    }


def creer_preuve(type_preuve, valeur, contexte=None):
    return {
        "source": "Debian Security Tracker",
        "type": type_preuve,
        "valeur": valeur,
        "contexte": contexte or {},
    }


def test_accepte_une_reference_structuree_pour_candidate():
    resultat = creer_resultat(
        preuves=[
            creer_preuve(
                "reference",
                "https://example.org/advisory",
            )
        ]
    )

    assert valider_resultat_connecteur_cve(resultat) is True


@pytest.mark.parametrize(
    "preuve",
    [
        {},
        {
            "source": "",
            "type": "reference",
            "valeur": "https://example.org/advisory",
            "contexte": {},
        },
        {
            "source": "NVD",
            "type": "",
            "valeur": "https://example.org/advisory",
            "contexte": {},
        },
        {
            "source": "NVD",
            "type": "reference",
            "valeur": "",
            "contexte": {},
        },
        {
            "source": "NVD",
            "type": "reference",
            "valeur": "https://example.org/advisory",
            "contexte": "Debian",
        },
    ],
)
def test_rejette_une_preuve_structuree_invalide(preuve):
    resultat = creer_resultat(preuves=[preuve])

    assert valider_resultat_connecteur_cve(resultat) is False


def test_rejette_une_vulnerabilite_confirmee_avec_une_simple_reference():
    resultat = creer_resultat(
        statut="affectee_confirmee",
        preuves=[
            creer_preuve(
                "reference",
                "https://example.org/advisory",
            )
        ],
    )
    resultat["resultats"][0]["versions_affectees"] = ["1.0 à 1.2"]

    assert valider_resultat_connecteur_cve(resultat) is False


def test_accepte_une_preuve_explicite_d_applicabilite():
    resultat = creer_resultat(
        statut="affectee_confirmee",
        preuves=[
            creer_preuve(
                "applicabilite_confirmee",
                "La version installée appartient à la plage affectée.",
                {
                    "version_installee": "1.2",
                    "version_affectee": "1.0 à 1.2",
                },
            ),
            creer_preuve(
                "version_installee",
                "1.2",
                {"version_installee": "1.2"},
            ),
        ],
    )
    resultat["resultats"][0]["version_source_installee"] = "1.2"
    resultat["resultats"][0]["versions_affectees"] = ["1.0 à 1.2"]

    assert valider_resultat_connecteur_cve(resultat) is True


def test_rejette_non_affectee_sans_preuve_de_non_applicabilite():
    resultat = creer_resultat(
        statut="non_affectee",
        preuves=[
            creer_preuve(
                "statut_officiel",
                "open",
            )
        ],
    )

    assert valider_resultat_connecteur_cve(resultat) is False


def test_accepte_non_affectee_avec_preuve_explicite():
    resultat = creer_resultat(
        statut="non_affectee",
        preuves=[
            creer_preuve(
                "non_applicabilite",
                "fixed_version=0",
                {"distribution": "trixie"},
            )
        ],
    )

    assert valider_resultat_connecteur_cve(resultat) is True


def test_rejette_correctif_disponible_sans_preuve_de_version_corrigee():
    resultat = creer_resultat(
        statut="correctif_disponible",
        preuves=[
            creer_preuve(
                "reference",
                "https://example.org/advisory",
            )
        ],
    )
    resultat["resultats"][0]["version_corrigee"] = "1.2.3"

    assert valider_resultat_connecteur_cve(resultat) is False


def test_accepte_correctif_avec_preuve_de_version_corrigee():
    resultat = creer_resultat(
        statut="correctif_disponible",
        preuves=[
            creer_preuve(
                "version_corrigee",
                "1.2.3",
                {"distribution": "trixie"},
            )
        ],
    )
    resultat["resultats"][0]["version_corrigee"] = "1.2.3"

    assert valider_resultat_connecteur_cve(resultat) is True


def test_rejette_applicabilite_confirmee_sans_version_installee():
    resultat = creer_resultat(
        statut="affectee_confirmee",
        preuves=[
            creer_preuve(
                "applicabilite_confirmee",
                "Applicabilité confirmée",
                {},
            )
        ],
    )
    resultat["resultats"][0]["versions_affectees"] = ["1.0 à 1.2"]

    assert valider_resultat_connecteur_cve(resultat) is False


def test_rejette_non_affectee_avec_mauvaise_valeur():
    resultat = creer_resultat(
        statut="non_affectee",
        preuves=[
            creer_preuve(
                "non_applicabilite",
                "open",
            )
        ],
    )

    assert valider_resultat_connecteur_cve(resultat) is False


def test_rejette_correctif_avec_version_differente():
    resultat = creer_resultat(
        statut="correctif_disponible",
        preuves=[
            creer_preuve(
                "version_corrigee",
                "1.2.2",
            )
        ],
    )
    resultat["resultats"][0]["version_corrigee"] = "1.2.3"

    assert valider_resultat_connecteur_cve(resultat) is False


def test_rejette_une_preuve_structuree_sans_contexte():
    resultat = creer_resultat(
        preuves=[
            {
                "source": "NVD",
                "type": "reference",
                "valeur": "https://example.org/advisory",
            }
        ],
    )

    assert valider_resultat_connecteur_cve(resultat) is False


def test_rejette_un_contexte_non_dictionnaire():
    resultat = creer_resultat(
        preuves=[
            {
                "source": "NVD",
                "type": "reference",
                "valeur": "https://example.org/advisory",
                "contexte": ["Debian"],
            }
        ],
    )

    assert valider_resultat_connecteur_cve(resultat) is False


def test_rejette_applicabilite_avec_versions_contradictoires():
    resultat = creer_resultat(
        statut="affectee_confirmee",
        preuves=[
            creer_preuve(
                "applicabilite_confirmee",
                "La version installée appartient à la plage affectée.",
                {"version_installee": "1.2"},
            ),
            creer_preuve(
                "version_installee",
                "1.3",
                {"version_installee": "1.3"},
            ),
        ],
    )
    resultat["resultats"][0]["version_source_installee"] = "1.3"
    resultat["resultats"][0]["versions_affectees"] = ["1.0 à 1.2"]

    assert valider_resultat_connecteur_cve(resultat) is False
