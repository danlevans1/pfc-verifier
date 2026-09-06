import json
import urllib.request

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
DEFAULT_MODEL = "gpt-oss:20b"


def ask_ollama(prompt: str, model: str = DEFAULT_MODEL) -> dict:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "stream": False,
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))

    return {
        "provider": "ollama",
        "model": result.get("model"),
        "content": result.get("message", {}).get("content"),
        "done": result.get("done"),
        "done_reason": result.get("done_reason"),
    }
