"""Normalisation locale des avis du Debian Security Tracker."""

import json
import re
from collections.abc import Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


from collections.abc import Mapping
import re


_IDENTIFIANT_CVE = re.compile(r"^CVE-\d{4}-\d{4,}$")


def normaliser_avis_debian(
    avis: object,
    distribution: str,
) -> list[dict]:
    """Normalise les avis Debian pour une distribution donnée.

    Cette fonction ne vérifie pas les versions des paquets installés.
    Elle décrit uniquement les informations publiées par le tracker.
    """
    if not isinstance(avis, Mapping) or not distribution:
        return []

    resultat = []

    for paquet_source, cves in avis.items():
        if not isinstance(paquet_source, str) or not isinstance(cves, Mapping):
            continue

        for identifiant, details in cves.items():
            if not isinstance(identifiant, str):
                continue
            if not _IDENTIFIANT_CVE.fullmatch(identifiant):
                continue
            if not isinstance(details, Mapping):
                continue

            releases = details.get("releases")
            if not isinstance(releases, Mapping):
                continue

            release = releases.get(distribution)
            if not isinstance(release, Mapping):
                continue

            statut_officiel = release.get("status")
            version_corrigee = release.get("fixed_version")

            if version_corrigee == "0":
                statut = "non_affectee"
                version_corrigee = None
            elif statut_officiel == "resolved" and isinstance(
                version_corrigee, str
            ) and version_corrigee:
                statut = "correctif_disponible"
            elif statut_officiel == "open":
                statut = "potentiellement_affectee"
                version_corrigee = None
            else:
                statut = "verification_incomplete"
                version_corrigee = None

            repositories = release.get("repositories")
            if not isinstance(repositories, Mapping):
                repositories = {}

            version_archive = repositories.get(distribution)
            if not isinstance(version_archive, str):
                version_archive = None

            description = details.get("description")
            if not isinstance(description, str):
                description = ""

            urgence = release.get("urgency")
            if not isinstance(urgence, str):
                urgence = None

            resultat.append(
                {
                    "identifiant": identifiant,
                    "paquet_source": paquet_source,
                    "distribution": distribution,
                    "description": description,
                    "statut": statut,
                    "statut_officiel": statut_officiel,
                    "version_corrigee": version_corrigee,
                    "version_archive": version_archive,
                    "urgence": urgence,
                    "source": (
                        "Debian Security Tracker "
                        "(export JSON)"
                    ),
                }
            )

    return resultat


URL_TRACKER_DEBIAN = (
    "https://security-tracker.debian.org/tracker/data/json"
)
TAILLE_MAX_JSON = 128 * 1024 * 1024


class ErreurTrackerDebian(Exception):
    """Erreur de récupération ou de validation du tracker Debian."""


def charger_avis_debian(timeout: int = 20) -> dict:
    """Télécharge et valide l'export JSON officiel Debian."""
    if not isinstance(timeout, int) or isinstance(timeout, bool):
        raise ValueError("Le délai doit être un entier positif.")
    if not 1 <= timeout <= 60:
        raise ValueError("Le délai doit être compris entre 1 et 60 secondes.")

    requete = Request(
        URL_TRACKER_DEBIAN,
        headers={
            "User-Agent": "LabPilot-security-audit/1.0",
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(requete, timeout=timeout) as reponse:
            headers = reponse.headers
            if hasattr(headers, "get_content_type"):
                contenu_type = headers.get_content_type()
            else:
                contenu_type = headers.get("Content-Type", "").split(";")[0].strip().lower()

            if contenu_type != "application/json":
                raise ErreurTrackerDebian(
                    "Le tracker n'a pas renvoyé du JSON."
                )

            longueur = headers.get("Content-Length")
            if longueur is not None:
                try:
                    if int(longueur) > TAILLE_MAX_JSON:
                        raise ErreurTrackerDebian(
                            "La réponse du tracker est trop volumineuse."
                        )
                except ValueError as erreur:
                    raise ErreurTrackerDebian(
                        "Taille de réponse HTTP invalide."
                    ) from erreur

            contenu = reponse.read(TAILLE_MAX_JSON + 1)

            if len(contenu) > TAILLE_MAX_JSON:
                raise ErreurTrackerDebian(
                    "La réponse du tracker dépasse la taille autorisée."
                )

    except (HTTPError, URLError, TimeoutError, OSError) as erreur:
        raise ErreurTrackerDebian(
            f"Échec de communication avec le tracker ({type(erreur).__name__})."
        ) from erreur

    try:
        donnees = json.loads(contenu)
    except (json.JSONDecodeError, UnicodeDecodeError) as erreur:
        raise ErreurTrackerDebian(
            "Le tracker a renvoyé un JSON invalide."
        ) from erreur

    if not isinstance(donnees, dict):
        raise ErreurTrackerDebian(
            "La racine du JSON doit être un objet."
        )

    return donnees

def comparer_versions_debian(version_a: str, version_b: str) -> int:
    """Compare deux versions Debian sans dépendance système."""
    if not isinstance(version_a, str) or not isinstance(version_b, str):
        raise ValueError("Les versions doivent être des chaînes non vides.")

    if not version_a or not version_b:
        raise ValueError("Les versions doivent être des chaînes non vides.")

    def decouper(version: str) -> tuple[int, str, str]:
        epoch = 0
        reste = version

        if ":" in reste:
            prefixe, candidat = reste.split(":", 1)
            if not prefixe.isdigit() or not candidat:
                raise ValueError(f"Version Debian invalide : {version!r}")
            epoch = int(prefixe)
            reste = candidat

        if "-" in reste:
            amont, revision = reste.rsplit("-", 1)
        else:
            amont, revision = reste, "0"

        if not amont or not revision or not amont[0].isdigit():
            raise ValueError(f"Version Debian invalide : {version!r}")

        return epoch, amont, revision

    def ordre_caractere(caractere: str | None) -> int:
        if caractere == "~":
            return -1
        if caractere is None:
            return 0
        if caractere.isalpha() and caractere.isascii():
            return ord(caractere)
        if caractere.isdigit() and caractere.isascii():
            return 0
        return ord(caractere) + 256

    def comparer_parties(a: str, b: str) -> int:
        i = j = 0

        while i < len(a) or j < len(b):
            # Comparer d'abord les caractères non numériques.
            while (
                (i < len(a) and not a[i].isascii() or
                 i < len(a) and not a[i].isdigit())
                or (j < len(b) and not b[j].isascii() or
                    j < len(b) and not b[j].isdigit())
            ):
                ca = a[i] if i < len(a) and not a[i].isdigit() else None
                cb = b[j] if j < len(b) and not b[j].isdigit() else None

                oa = ordre_caractere(ca)
                ob = ordre_caractere(cb)

                if oa != ob:
                    return -1 if oa < ob else 1

                if ca is not None:
                    i += 1
                if cb is not None:
                    j += 1

            # Comparer les suites numériques sans convertir en entier.
            debut_a, debut_b = i, j

            while i < len(a) and a[i].isascii() and a[i].isdigit():
                i += 1
            while j < len(b) and b[j].isascii() and b[j].isdigit():
                j += 1

            chiffres_a = a[debut_a:i].lstrip("0")
            chiffres_b = b[debut_b:j].lstrip("0")

            if len(chiffres_a) != len(chiffres_b):
                return -1 if len(chiffres_a) < len(chiffres_b) else 1
            if chiffres_a != chiffres_b:
                return -1 if chiffres_a < chiffres_b else 1

        return 0

    epoch_a, amont_a, revision_a = decouper(version_a)
    epoch_b, amont_b, revision_b = decouper(version_b)

    if epoch_a != epoch_b:
        return -1 if epoch_a < epoch_b else 1

    resultat = comparer_parties(amont_a, amont_b)
    if resultat:
        return resultat

    return comparer_parties(revision_a, revision_b)


class ErreurInventairePaquetsDebian(Exception):
    """Erreur de validation de l'inventaire des paquets Debian."""


def normaliser_inventaire_paquets_debian(sortie: object) -> list[dict]:
    """Analyse la sortie tabulée de dpkg-query sans ignorer les lignes invalides."""
    if not isinstance(sortie, str) or not sortie.strip():
        raise ErreurInventairePaquetsDebian(
            "La sortie de l'inventaire des paquets est vide ou invalide."
        )

    paquets = []
    noms_vus = set()

    for numero_ligne, ligne in enumerate(sortie.splitlines(), start=1):
        if not ligne:
            continue

        champs = ligne.split("\t")
        if len(champs) != 4:
            raise ErreurInventairePaquetsDebian(
                f"Ligne {numero_ligne} : quatre champs attendus."
            )

        nom, version, paquet_source, version_source = champs

        if not nom or not version or not paquet_source or not version_source:
            raise ErreurInventairePaquetsDebian(
                f"Ligne {numero_ligne} : champ obligatoire manquant."
            )

        if any(
            caractere.isspace()
            for valeur in champs
            for caractere in valeur
        ):
            raise ErreurInventairePaquetsDebian(
                f"Ligne {numero_ligne} : espace inattendu dans un champ."
            )

        if nom in noms_vus:
            raise ErreurInventairePaquetsDebian(
                f"Ligne {numero_ligne} : paquet dupliqué."
            )

        noms_vus.add(nom)
        paquets.append({
            "nom": nom,
            "version": version,
            "paquet_source": paquet_source,
            "version_source": version_source,
        })

    if not paquets:
        raise ErreurInventairePaquetsDebian(
            "Aucun paquet valide dans la sortie reçue."
        )

    return paquets


def rapprocher_avis_debian_paquet(
    avis: Mapping,
    paquet_source: str,
    version_source_installee: str,
    distribution: str,
) -> list[dict]:
    """Rapproche un inventaire source des avis Debian sans surconfirmer.

    Une version installée antérieure à fixed_version indique qu'un correctif
    connu est postérieur à cette version. Cela ne suffit pas à confirmer
    l'applicabilité d'une CVE : le statut reste prudent.
    """
    if not isinstance(avis, Mapping):
        raise ValueError("Les avis Debian doivent être un objet de mapping.")

    if not all(
        isinstance(valeur, str) and valeur.strip()
        for valeur in (
            paquet_source,
            version_source_installee,
            distribution,
        )
    ):
        raise ValueError("Paquet, version et distribution sont obligatoires.")

    entrees = avis.get(paquet_source)
    if not isinstance(entrees, Mapping):
        return []

    avis_normalises = normaliser_avis_debian(
        {paquet_source: entrees},
        distribution,
    )
    resultats = []

    for entree in avis_normalises:
        statut = entree["statut"]
        version_corrigee = entree["version_corrigee"]
        preuve = [
            "Source : Debian Security Tracker (export JSON).",
            f"Distribution examinée : {distribution}.",
            f"Paquet source : {paquet_source}.",
            f"Version source installée : {version_source_installee}.",
            f"Statut officiel : {entree['statut_officiel']!r}.",
        ]

        if statut == "correctif_disponible" and version_corrigee:
            try:
                comparaison = comparer_versions_debian(
                    version_source_installee,
                    version_corrigee,
                )
            except ValueError:
                statut = "verification_incomplete"
                preuve.append(
                    "Comparaison impossible : version Debian invalide."
                )
            else:
                if comparaison < 0:
                    preuve.append(
                        f"La version corrigée publiée est {version_corrigee}."
                    )
                else:
                    # La comparaison à fixed_version seule ne permet pas
                    # d'affirmer l'applicabilité ni l'absence de risque.
                    statut = "verification_incomplete"
                    preuve.append(
                        "La version installée n'est pas antérieure à "
                        "fixed_version ; aucune conclusion automatique."
                    )

        elif statut == "non_affectee":
            preuve.append(
                "Le tracker indique fixed_version=0 pour cette distribution."
            )
        elif statut == "potentiellement_affectee":
            preuve.append(
                "Le tracker indique un statut open ; l'applicabilité "
                "à la version installée reste à vérifier."
            )
        else:
            statut = "verification_incomplete"
            preuve.append(
                "Les données officielles ne permettent pas une conclusion "
                "automatique sur la version installée."
            )

        resultats.append({
            "identifiant": entree["identifiant"],
            "versions_affectees": [],
            "version_corrigee": version_corrigee,
            "statut": statut,
            "preuve": preuve,
            "date_verification": None,
        })

    return resultats
