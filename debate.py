"""
debate.py — Debate orchestration: state machine, voting system.

The debate flow:
  1. Thinker(s) propose initial solutions.
  2. Critic(s) critique and propose alternatives.
  3. Thinker(s) revise based on criticism.
  4. Critic(s) re-evaluate the revision.
  5. Judge(s) review full debate and give final verdict.
  6. All agents vote: APPROVE / REJECT / NEEDS REVISION.
     - Majority approves → "Council Approved ✅"
     - Otherwise → revision round (up to MAX_REVISION_ROUNDS extra rounds)
"""

import re
from typing import Callable, Optional

from config import MAX_REVISION_ROUNDS, VOTE_OPTIONS, PROVIDERS
from agents import Agent, build_messages, build_vote_messages
from providers import chat
from rate_limiter import get_registry


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _call_agent(agent: Agent, messages: list[dict],
                on_fallback: Optional[Callable[[str, str], None]] = None) -> str:
    """
    Call the agent's provider, falling back to another provider if rate-limited.
    Records the request in the rate limiter.
    """
    registry = get_registry()
    provider = agent.provider
    model = agent.model

    if not registry.can_request(provider):
        fallback = registry.find_available_fallback(provider)
        if fallback is None:
            raise RuntimeError("All providers are currently rate-limited. Please wait.")
        if on_fallback:
            on_fallback(provider, fallback)
        provider = fallback
        model = PROVIDERS[fallback]["default_model"]

    registry.record_request(provider)
    return chat(provider, messages, model)


# ---------------------------------------------------------------------------
# Step dataclass
# ---------------------------------------------------------------------------

class DebateStep:
    """Represents a single step in the debate."""

    def __init__(self, agent: Agent, step_type: str, content: str,
                 used_provider: str = "", used_model: str = ""):
        self.agent = agent
        self.step_type = step_type   # "proposal" | "critique" | "revision" | "re-eval" | "verdict" | "vote"
        self.content = content
        self.used_provider = used_provider or agent.provider
        self.used_model = used_model or agent.model

    def to_history_entry(self) -> dict:
        return {
            "agent_id": self.agent.id,
            "agent_name": self.agent.name,
            "role": self.agent.role,
            "step_type": self.step_type,
            "content": self.content,
            "provider": self.used_provider,
            "model": self.used_model,
        }


# ---------------------------------------------------------------------------
# Debate runner
# ---------------------------------------------------------------------------

def run_debate(
    question: str,
    agents: list[Agent],
    context_text: str = "",
    on_step: Optional[Callable[[DebateStep], None]] = None,
    on_fallback: Optional[Callable[[str, str], None]] = None,
) -> dict:
    """
    Orchestrate the full AI Council debate.

    `on_step` is called after each DebateStep so callers (e.g. Streamlit)
    can stream results progressively.

    Returns a result dict with keys:
        steps         — list of all DebateStep objects
        history       — flat conversation history (list of dicts)
        final_answer  — the judge's final verdict text
        votes         — list of vote dicts
        approved      — bool
        vote_summary  — human-readable tally
    """
    history: list[dict] = []
    steps: list[DebateStep] = []

    # Partition agents by role
    thinkers = [a for a in agents if a.role == "thinker"]
    critics  = [a for a in agents if a.role == "critic"]
    judges   = [a for a in agents if a.role == "judge"]
    others   = [a for a in agents if a.role not in ("thinker", "critic", "judge")]

    # Ensure we have at least one of each; use first available as fallback
    if not thinkers:
        thinkers = agents[:1]
    if not critics:
        critics = agents[1:2] or agents[:1]
    if not judges:
        judges = agents[-1:] or agents[:1]

    def emit(step: DebateStep) -> None:
        steps.append(step)
        history.append(step.to_history_entry())
        if on_step:
            on_step(step)

    def _run_agent(agent: Agent, step_type: str) -> DebateStep:
        msgs = build_messages(agent, history, question, context_text or None)
        content = _call_agent(agent, msgs, on_fallback)
        return DebateStep(agent, step_type, content)

    # ------------------------------------------------------------------
    # Phase 1: Thinkers propose
    # ------------------------------------------------------------------
    for thinker in thinkers:
        emit(_run_agent(thinker, "proposal"))

    # ------------------------------------------------------------------
    # Phase 2: Critics critique
    # ------------------------------------------------------------------
    for critic in critics:
        emit(_run_agent(critic, "critique"))

    # ------------------------------------------------------------------
    # Phase 3: Thinkers revise
    # ------------------------------------------------------------------
    for thinker in thinkers:
        emit(_run_agent(thinker, "revision"))

    # ------------------------------------------------------------------
    # Phase 4: Critics re-evaluate
    # ------------------------------------------------------------------
    for critic in critics:
        emit(_run_agent(critic, "re-evaluation"))

    # ------------------------------------------------------------------
    # Phase 5: Other specialist agents (researcher, security_auditor, etc.)
    # ------------------------------------------------------------------
    for agent in others:
        emit(_run_agent(agent, "specialist"))

    # ------------------------------------------------------------------
    # Phase 6: Judges give verdict
    # ------------------------------------------------------------------
    final_answer = ""
    for judge in judges:
        step = _run_agent(judge, "verdict")
        emit(step)
        final_answer = step.content  # last judge wins

    # ------------------------------------------------------------------
    # Phase 7: Voting round
    # ------------------------------------------------------------------
    votes = []
    revision_rounds = 0

    while True:
        votes = _collect_votes(agents, question, final_answer, on_fallback)
        approved, summary = _tally_votes(votes)

        if approved or revision_rounds >= MAX_REVISION_ROUNDS:
            break

        # Majority rejected → run a revision
        revision_rounds += 1

        # Ask thinkers to revise once more
        for thinker in thinkers:
            extra_prompt = (
                f"The council voted: {summary}. "
                "Please revise your solution to address the concerns raised."
            )
            msgs = build_messages(thinker, history, question + "\n\n" + extra_prompt,
                                  context_text or None)
            content = _call_agent(thinker, msgs, on_fallback)
            step = DebateStep(thinker, "revision", content)
            emit(step)

        # Ask judges to re-assess
        for judge in judges:
            step = _run_agent(judge, "verdict")
            emit(step)
            final_answer = step.content

    approved, vote_summary = _tally_votes(votes)

    return {
        "steps": steps,
        "history": history,
        "final_answer": final_answer,
        "votes": votes,
        "approved": approved,
        "vote_summary": vote_summary,
    }


def _collect_votes(agents: list[Agent], question: str,
                   final_answer: str,
                   on_fallback: Optional[Callable] = None) -> list[dict]:
    votes = []
    for agent in agents:
        msgs = build_vote_messages(agent, question, final_answer)
        try:
            raw = _call_agent(agent, msgs, on_fallback)
        except Exception as exc:  # noqa: BLE001
            # Agent unreachable: cast a neutral vote so it doesn't sway consensus
            raw = f"NEEDS REVISION\n(Agent unavailable: {exc})"

        vote_value, reason = _parse_vote(raw)
        votes.append({
            "agent_id": agent.id,
            "agent_name": agent.name,
            "role": agent.role,
            "vote": vote_value,
            "reason": reason,
            "raw": raw,
        })
    return votes


def _parse_vote(text: str) -> tuple[str, str]:
    """Extract the vote keyword and the reason from the agent's reply."""
    text = text.strip()
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    for option in VOTE_OPTIONS:
        if lines and option in lines[0].upper():
            reason = " ".join(lines[1:]) if len(lines) > 1 else ""
            return option, reason

    # Fallback: scan whole text
    for option in VOTE_OPTIONS:
        if option in text.upper():
            return option, text
    return "APPROVE", text


def _tally_votes(votes: list[dict]) -> tuple[bool, str]:
    """Return (approved, human-readable summary)."""
    counts: dict[str, int] = {v: 0 for v in VOTE_OPTIONS}
    for v in votes:
        counts[v["vote"]] = counts.get(v["vote"], 0) + 1

    total = len(votes)
    approve_count = counts.get("APPROVE", 0)
    reject_count = counts.get("REJECT", 0)
    revision_count = counts.get("NEEDS REVISION", 0)

    summary_parts = [f"APPROVE: {approve_count}/{total}",
                     f"REJECT: {reject_count}/{total}",
                     f"NEEDS REVISION: {revision_count}/{total}"]
    summary = " | ".join(summary_parts)

    approved = approve_count > (total / 2)
    return approved, summary
