"""Lightweight agent wrapper around the existing chat handler.

This module introduces a simple ``ChatAgent`` that retains its own state
and follows the classic perception → planning → action loop.  By default the
planning stage simply delegates to ``core.ai_orchestrator.handle_chat`` so
behaviour is identical to the prior implementation.  The purpose of the
wrapper is to provide a clean place for future agentic enhancements without
modifying the large ``ai_orchestrator`` module.

Usage examples::

    from core.agent import chat_agent
    response = chat_agent.handle_message("hello")

Advanced subclasses may override ``perceive``, ``plan`` or ``act`` to
integrate additional observables, chain-of-thought reasoning, or external
effects.
"""

from typing import Any

from core import ai_orchestrator


class ChatAgent:
    STATE_FILE = "agent_state.json"

    def __init__(self) -> None:
        # the agent maintains its own mutable state dict; this is mostly
        # here so that we can eventually persist or swap it without touching
        # the global ``conversation_state`` in ai_orchestrator.
        self.state: dict[str, Any] = {}
        # load persisted state if available, otherwise initialize a fresh one
        self._load_state()

    def _load_state(self) -> None:
        try:
            import json
            with open(self.STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # update the conversation state in orchestrator as well
            ai_orchestrator.conversation_state.update(data)
            self.state = ai_orchestrator.conversation_state
        except Exception:
            # file missing or corrupt → start fresh
            self.reset_state()

    def _save_state(self) -> None:
        try:
            import json
            with open(self.STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except Exception:
            pass

    def reset_state(self) -> None:
        """Clear the conversation state to start a fresh session."""
        # simply delegate to the existing reset_state helper for parity
        ai_orchestrator.reset_state()
        # and keep a shallow alias so both dicts stay in sync
        self.state = ai_orchestrator.conversation_state

    # --------------------------------------------------------------
    # agentic stages (overridable)
    # --------------------------------------------------------------
    def perceive(self, user_message: str) -> None:
        """Record observations.  By default we just store the last message."""
        self.state["last_msg"] = user_message

    def plan(self, user_message: str) -> dict[str, Any]:
        """Decide what to do next.

        We treat shipping-related messages as high-priority directives that must
        invoke the core handler; RAG is only consulted when the incoming text
        appears unrelated to the logistics domain and no flow is active.
        """
        # quick intent check using the existing helper
        try:
            from core.ai_orchestrator import detect_intent
            intent = detect_intent(user_message)
        except Exception:
            intent = None

        # if we're already inside a flow or the user is clearly asking about
        # shipping/quote/track/label, delegate directly; this avoids RAG
        # hijacking the conversation with documentation.
        if intent is not None or self.state.get("flow_mode") is not None:
            return ai_orchestrator.handle_chat(user_message)

        # otherwise try the retrieval engine first
        try:
            from core import ai_orchestrator as _o
            rag_answer = _o.rag_engine.query(user_message)
            if rag_answer is not None:
                try:
                    _o.rag_engine.add_memory(f"user: {user_message}\nassistant: {rag_answer}")
                except Exception:
                    pass
                return {"response": rag_answer}
        except Exception:
            pass

        # no special handling needed → normal chat logic
        return ai_orchestrator.handle_chat(user_message)

    def act(self, result: dict[str, Any]) -> dict[str, Any]:
        """Perform side-effects or post-process the plan result.  Stubbed."""
        return result

    def handle_message(self, user_message: str) -> dict[str, Any]:
        """Full agent loop invoked by external callers."""
        self.perceive(user_message)
        plan_result = self.plan(user_message)
        result = self.act(plan_result)
        # persist state after every turn so that the agent can recover if the
        # process is restarted or the conversation is resumed later.
        self._save_state()
        return result


# singleton instance for convenience
chat_agent = ChatAgent()
