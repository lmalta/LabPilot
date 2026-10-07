import json
import urllib.request

from .configuration import OLLAMA_MODEL, OLLAMA_URL
from .tools import DEFINITIONS_OUTILS


def interroger_ollama(messages: list[dict[str, str]]) -> dict:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "tools": DEFINITIONS_OUTILS,
        "stream": False,
        "think": False,
    }

    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request) as response:
        result = json.loads(response.read().decode("utf-8"))

    return result["message"]
