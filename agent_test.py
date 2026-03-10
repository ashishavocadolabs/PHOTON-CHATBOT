from core.agent import chat_agent

for msg in ["i want ship", "get quote", "print label"]:
    print(f"message: {msg}")
    resp = chat_agent.handle_message(msg)
    print(resp)
