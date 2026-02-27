"""
agents.py — Agent definitions, system prompts, and role management.
"""

import uuid
from dataclasses import dataclass, field
from typing import Optional

from config import ROLES, PROVIDERS, DEFAULT_AGENTS


@dataclass
class Agent:
    """Represents a single AI council member."""
    id: str
    name: str
    role: str          # key from ROLES
    provider: str      # key from PROVIDERS
    model: str

    @property
    def role_cfg(self) -> dict:
        return ROLES.get(self.role, {})

    @property
    def provider_cfg(self) -> dict:
        return PROVIDERS.get(self.provider, {})

    @property
    def color(self) -> str:
        return self.role_cfg.get("color", "#888888")

    @property
    def icon(self) -> str:
        return self.role_cfg.get("icon", "🤖")

    @property
    def system_prompt(self) -> str:
        return self.role_cfg.get("system_prompt", "You are a helpful assistant.")

    @property
    def display_label(self) -> str:
        role_label = self.role_cfg.get("label", self.role.capitalize())
        provider_name = self.provider_cfg.get("name", self.provider)
        return f"{self.icon} {self.name} [{role_label} · {provider_name} / {self.model}]"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "provider": self.provider,
            "model": self.model,
        }


def agent_from_dict(data: dict) -> Agent:
    return Agent(
        id=data.get("id", str(uuid.uuid4())),
        name=data["name"],
        role=data["role"],
        provider=data["provider"],
        model=data["model"],
    )


def default_council() -> list[Agent]:
    """Return the default set of council agents."""
    return [agent_from_dict(d) for d in DEFAULT_AGENTS]


def build_messages(agent: Agent, conversation: list[dict],
                   user_question: str,
                   context_text: Optional[str] = None) -> list[dict]:
    """
    Build an OpenAI-style messages list for the agent.

    `conversation` is the running debate history in the form:
        [{"role": "agent_name", "content": "...", "agent_id": "..."}, ...]

    We flatten this into a system + user/assistant structure the LLM understands.
    """
    messages: list[dict] = [{"role": "system", "content": agent.system_prompt}]

    # Build a context block for the user message
    parts: list[str] = []

    if context_text:
        parts.append(f"## Attached Context\n{context_text}\n")

    parts.append(f"## Question\n{user_question}\n")

    if conversation:
        parts.append("## Debate So Far")
        for entry in conversation:
            speaker = entry.get("agent_name", entry.get("role", "Unknown"))
            parts.append(f"**{speaker}:**\n{entry['content']}\n")

    messages.append({"role": "user", "content": "\n".join(parts)})
    return messages


def build_vote_messages(agent: Agent, question: str,
                        final_answer: str) -> list[dict]:
    """Build messages asking an agent to vote on the final answer."""
    prompt = (
        f"## Question\n{question}\n\n"
        f"## Proposed Final Answer\n{final_answer}\n\n"
        "Based on the above, cast your vote. Reply with EXACTLY one of:\n"
        "- APPROVE\n"
        "- REJECT\n"
        "- NEEDS REVISION\n\n"
        "Then on the next line provide a brief (1–2 sentence) reason for your vote."
    )
    return [
        {"role": "system", "content": agent.system_prompt},
        {"role": "user", "content": prompt},
    ]
