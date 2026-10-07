from labpilot.ollama import interroger_ollama


def main() -> None:
    reponse = interroger_ollama(
        "Réponds simplement : LabPilot fonctionne."
    )
    print(reponse)


if __name__ == "__main__":
    main()