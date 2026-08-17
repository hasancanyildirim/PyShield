"""Simple mock Target AI for the QA Safe MVP."""

def get_response(prompt: str) -> str:
    text = prompt.lower()

    if "system prompt" in text or "system instruction" in text:
        return "I cannot reveal my system prompt or hidden instructions."
    if "ignore your previous instructions" in text:
        return "I cannot ignore my previous instructions."
    if "secret" in text or "confidential" in text:
        return "I cannot provide confidential or hidden information."

    return f"Target AI response: I received your request: {prompt}"
