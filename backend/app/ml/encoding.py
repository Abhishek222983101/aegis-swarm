"""Shared constants for the observation encoding used by both training (env.py,
needs gymnasium) and inference (inference.py, must NOT need gymnasium). Keeping
these here means inference.py stays importable in an environment where the
training extras were never installed."""
from __future__ import annotations

from app.sim.entities import AgentType

AGENT_TYPES = list(AgentType)
N_AGENT_TYPES = len(AGENT_TYPES)
WORLD_SIZE = 400.0
