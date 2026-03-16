from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Required, TypedDict


class AgentMessageRecord(TypedDict):
    sender: Required[str]
    recipient: Required[str]
    content: Required[str]


@dataclass(slots=True, frozen=True)
class AgentMessage:
    sender: str
    recipient: str
    content: str

    def to_dict(self) -> AgentMessageRecord:
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "content": self.content,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "AgentMessage":
        return cls(
            sender=_required_text(data, "sender"),
            recipient=_required_text(data, "recipient"),
            content=_required_text(data, "content"),
        )

    @classmethod
    def from_dicts(cls, items: Iterable[Mapping[str, object]]) -> list["AgentMessage"]:
        return [cls.from_dict(item) for item in items]

    @staticmethod
    def to_dicts(items: Iterable["AgentMessage"]) -> list[AgentMessageRecord]:
        return [item.to_dict() for item in items]


def _required_text(data: Mapping[str, object], key: str) -> str:
    value = str(data[key]).strip()
    if not value:
        raise ValueError(f"Agent message field '{key}' cannot be empty.")
    return value
