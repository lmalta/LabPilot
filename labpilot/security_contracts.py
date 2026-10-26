"""Contrat commun et validation des résultats de sécurité CVE."""


STATUTS_CVE_AUTORISES = frozenset({
    "candidate",
    "potentiellement_affectee",
    "affectee_confirmee",
    "non_affectee",
    "correctif_disponible",
    "verification_incomplete",
})


def valider_resultat_connecteur_cve(resultat: dict) -> bool:
    """Valide la structure commune d'un résultat de connecteur CVE."""
    if not isinstance(resultat, dict):
        return False

    if not all(
        isinstance(resultat.get(cle), str) and resultat[cle].strip()
        for cle in ("produit", "version_detectee", "source")
    ):
        return False

    if not isinstance(resultat.get("disponible"), bool):
        return False

    if resultat.get("erreur") is not None and not isinstance(
        resultat["erreur"], str
    ):
        return False

    if resultat["disponible"] and resultat["erreur"] is not None:
        return False

    resultats = resultat.get("resultats")
    if not isinstance(resultats, list):
        return False

    if not resultat["disponible"] and not resultat["erreur"]:
        return False

    if not resultat["disponible"] and resultat["resultats"]:
        return False

    for avis in resultats:
        if not isinstance(avis, dict):
            return False

        champs_obligatoires = {
            "identifiant",
            "versions_affectees",
            "version_corrigee",
            "statut",
            "preuve",
            "date_verification",
        }
        if not champs_obligatoires.issubset(avis):
            return False

        if not isinstance(avis.get("identifiant"), str) or not avis["identifiant"].strip():
            return False

        statut = avis.get("statut")
        if not isinstance(statut, str) or statut not in STATUTS_CVE_AUTORISES:
            return False

        if not isinstance(avis.get("versions_affectees"), list):
            return False

        if any(not isinstance(version, str) for version in avis["versions_affectees"]):
            return False

        version_corrigee = avis.get("version_corrigee")
        if version_corrigee is not None and not isinstance(version_corrigee, str):
            return False

        if not isinstance(avis.get("preuve"), list):
            return False

        if any(not isinstance(preuve, str) for preuve in avis["preuve"]):
            return False

        date_verification = avis["date_verification"]
        if date_verification is not None and not isinstance(date_verification, str):
            return False

        if date_verification is not None and not date_verification.strip():
            return False

        preuve = avis["preuve"]
        versions_affectees = avis["versions_affectees"]
        version_corrigee = avis["version_corrigee"]

        if avis["statut"] == "affectee_confirmee":
            if not versions_affectees or not any(p.strip() for p in preuve):
                return False

        if avis["statut"] == "non_affectee":
            if not any(p.strip() for p in preuve):
                return False

        if avis["statut"] == "correctif_disponible":
            if (
                not isinstance(version_corrigee, str)
                or not version_corrigee.strip()
                or not any(p.strip() for p in preuve)
            ):
                return False


    return True



def finaliser_resultat_connecteur_cve(
    resultat: dict,
    erreur_secours: str = "contrat_invalide",
) -> dict:
    """Garantit que le résultat respecte le contrat commun."""
    if valider_resultat_connecteur_cve(resultat):
        return resultat

    if not isinstance(resultat, dict):
        resultat = {}

    produit = resultat.get("produit")
    version = resultat.get("version_detectee")
    source = resultat.get("source")

    return {
        "produit": produit.strip()
        if isinstance(produit, str) and produit.strip()
        else "inconnu",
        "version_detectee": version.strip()
        if isinstance(version, str) and version.strip()
        else "inconnue",
        "source": source.strip()
        if isinstance(source, str) and source.strip()
        else "NVD",
        "disponible": False,
        "erreur": (
            erreur_secours
            if isinstance(erreur_secours, str) and erreur_secours.strip()
            else "contrat_invalide"
        ),
        "resultats": [],
    }
