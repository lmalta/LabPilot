import json
import sys

from .tools import OUTILS


def traiter_requete(requete: dict) -> dict:
    nom_outil = requete["name"]
    arguments = requete.get("arguments", {})

    outil = OUTILS.get(nom_outil)

    if outil is None:
        return {
            "success": False,
            "error": {
                "type": "OutilInconnu",
                "message": f'L outil "{nom_outil}" n existe pas.',
            },
        }

    try:
        resultat = outil(**arguments)

        return {
            "success": True,
            "result": resultat,
        }

    except Exception as erreur:
        return {
            "success": False,
            "error": {
                "type": type(erreur).__name__,
                "message": str(erreur),
            },
        }


def main() -> None:
    for ligne in sys.stdin:
        ligne = ligne.strip()

        if not ligne:
            continue

        try:
            requete = json.loads(ligne)
            reponse = traiter_requete(requete)
        except Exception as erreur:
            reponse = {
                "success": False,
                "error": {
                    "type": type(erreur).__name__,
                    "message": str(erreur),
                },
            }

        print(json.dumps(reponse, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
