"""Identification des systèmes et registre des connecteurs de sécurité."""

from dataclasses import dataclass
from typing import Any, Callable, Protocol
from labpilot.security_contracts import finaliser_resultat_connecteur_cve

@dataclass(frozen=True)
class SystemeDetecte:
    """Identité normalisée d'un système détecté."""

    famille: str
    produit: str
    version: str | None
    connecteur: str | None


class ConnecteurSecurite(Protocol):
    """Interface commune d'un connecteur de sécurité."""

    def __call__(
        self,
        systeme: SystemeDetecte,
    ) -> dict[str, Any]:
        """Retourne un résultat respectant le contrat CVE commun."""
        ...

# Un connecteur n'est enregistré que lorsqu'il est réellement implémenté.
# Les valeurs seront des fonctions de recherche/verification dédiées.
CONNECTEURS_SECURITE: dict[str, ConnecteurSecurite] = {}


def identifier_systeme(
    nom_os: str | None,
    version: str | None = None,
    noyau: str | None = None,
    nom_machine: str | None = None,
) -> SystemeDetecte:
    """Identifie un système sans supposer qu'un connecteur existe."""
    nom = nom_os.strip() if isinstance(nom_os, str) else ""
    nom_normalise = nom.casefold()
    noyau_normalise = noyau.casefold() if isinstance(noyau, str) else ""
    machine_normalisee = (
        nom_machine.strip().casefold()
        if isinstance(nom_machine, str)
        else ""
    )

    if (
        "truenas" in noyau_normalise
        or machine_normalisee in {"truenas", "truenas-scale"}
        or "truenas" in nom_normalise
    ):
        return SystemeDetecte("nas", "TrueNAS", version, "truenas")

    if (
        "home assistant os" in nom_normalise
        or noyau_normalise.endswith("-haos")
        or machine_normalisee.startswith("haos")
    ):
        return SystemeDetecte(
            "appliance",
            "Home Assistant OS",
            version,
            "home_assistant_os",
        )

    if "windows" in nom_normalise:
        return SystemeDetecte("windows", nom or "Windows", version, None)

    if "debian" in nom_normalise:
        return SystemeDetecte("linux", "Debian", version, "debian")

    if "ubuntu" in nom_normalise:
        return SystemeDetecte("linux", "Ubuntu", version, "ubuntu")

    if nom:
        return SystemeDetecte("inconnu", nom, version, None)

    return SystemeDetecte("inconnu", "Système non identifié", version, None)


def connecteur_disponible(systeme: SystemeDetecte) -> bool:
    """Indique si un connecteur réellement enregistré existe."""
    if not isinstance(systeme, SystemeDetecte):
        return False

    return (
        systeme.connecteur is not None
        and callable(CONNECTEURS_SECURITE.get(systeme.connecteur))
    )


def executer_connecteur_securite(systeme: SystemeDetecte) -> dict[str, Any]:
    """Exécute le connecteur enregistré et sécurise son résultat."""
    if not isinstance(systeme, SystemeDetecte):
        return finaliser_resultat_connecteur_cve(
            {},
            erreur_secours="systeme_invalide",
        )

    connecteur = CONNECTEURS_SECURITE.get(systeme.connecteur)

    if not callable(connecteur):
        return finaliser_resultat_connecteur_cve(
            {
                "produit": systeme.produit,
                "version_detectee": systeme.version or "inconnue",
                "source": systeme.connecteur or "aucun_connecteur",
                "disponible": False,
                "erreur": "connecteur_indisponible",
                "resultats": [],
            }
        )

    try:
        resultat = connecteur(systeme)
    except Exception:
        resultat = {
            "produit": systeme.produit,
            "version_detectee": systeme.version or "inconnue",
            "source": systeme.connecteur or "connecteur",
            "disponible": False,
            "erreur": "erreur_execution_connecteur",
            "resultats": [],
        }

    return finaliser_resultat_connecteur_cve(resultat)