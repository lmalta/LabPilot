from labpilot.agent import Agent


def main() -> None:
    agent = Agent()
    reponse = agent.executer(
        "Réponds simplement : LabPilot fonctionne."
    )
    print(reponse)


if __name__ == "__main__":
    main()