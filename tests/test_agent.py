from labpilot.agent import Agent


def test_creation_agent():
    agent = Agent()

    assert agent.historique
