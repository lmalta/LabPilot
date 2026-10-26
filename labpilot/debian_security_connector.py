"""Connecteur CVE Debian fondé sur l'inventaire réel des paquets."""

from datetime import datetime, timezone

from labpilot.debian_security import (
    ErreurTrackerDebian,
    charger_avis_debian,
    rapprocher_avis_debian_paquet,
)
from labpilot.proxmox_guest_agent import (
    ErreurCollectePaquetsDebian,
    inventaire_paquets_debian_proxmox,
)
from labpilot.security_contracts import finaliser_resultat_connecteur_cve


SOURCE = "Debian Security Tracker"
DISTRIBUTIONS_DEBIAN = {"11": "bullseye", "12": "bookworm", "13": "trixie"}


def auditer_paquets_debian_proxmox(
    noeud: str,
    vmid: int,
    version_os: str,
) -> dict:
    """Rapproche l'inventaire d'une VM Debian avec le tracker officiel."""
    resultat_base = {
        "produit": "Debian",
        "version_detectee": version_os,
        "source": SOURCE,
        "disponible": False,
        "erreur": None,
        "resultats": [],
    }

    distribution = DISTRIBUTIONS_DEBIAN.get(version_os.strip())
    if distribution is None:
        resultat_base["erreur"] = "distribution_debian_non_prise_en_charge"
        return finaliser_resultat_connecteur_cve(resultat_base)

    try:
        paquets = inventaire_paquets_debian_proxmox(noeud, vmid)
        avis_debian = charger_avis_debian()
    except (ErreurCollectePaquetsDebian, ErreurTrackerDebian):
        resultat_base["erreur"] = "source_securite_indisponible"
        return finaliser_resultat_connecteur_cve(resultat_base)

    groupes = {}

    for paquet in paquets:
        source = paquet.get("paquet_source")
        version_source = paquet.get("version_source")
        nom_binaire = paquet.get("nom")

        if (
            not isinstance(source, str)
            or not source.strip()
            or not isinstance(version_source, str)
            or not version_source.strip()
        ):
            continue

        cle = (source.strip(), version_source.strip())
        groupe = groupes.setdefault(
            cle,
            {"paquets_binaires": set()},
        )

        if isinstance(nom_binaire, str) and nom_binaire.strip():
            groupe["paquets_binaires"].add(nom_binaire.strip())

    resultats = []

    for (source, version_source), groupe in groupes.items():
        avis_paquet = rapprocher_avis_debian_paquet(
            avis_debian,
            source,
            version_source,
            distribution,
        )

        for avis in avis_paquet:
            avis["paquet_source"] = source
            avis["version_source_installee"] = version_source
            avis["paquets_binaires"] = sorted(
                groupe["paquets_binaires"]
            )

        resultats.extend(avis_paquet)

    # Un avis tracker n'est pas une preuve de vulnérabilité confirmée.
    # On conserve donc les statuts prudents issus du rapprochement.
    date_verification = datetime.now(timezone.utc).isoformat()
    for avis in resultats:
        avis["date_verification"] = date_verification

    resultat_base.update({
        "disponible": True,
        "resultats": resultats,
    })
    return finaliser_resultat_connecteur_cve(resultat_base)
