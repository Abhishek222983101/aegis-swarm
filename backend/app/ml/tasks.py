"""Task representation shared by the baseline algorithms and the trained policy."""
from __future__ import annotations

from dataclasses import dataclass

from app.sim.entities import AgentType


@dataclass
class Task:
    id: str
    position: tuple[float, float]
    required_type: AgentType | None = None  # None = any agent type can do it
    priority: int = 1  # higher = more urgent
