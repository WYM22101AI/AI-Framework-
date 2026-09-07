"""
Base agent class for the research system.
Provides LLM call abstraction, structured output, and DuckDB logging.

Agents call existing scripts as tools — they don't reimplement statistics or backtesting.
LLM is optional: some agents (regime) are pure code, others (governor) use LLM.
"""

import json
from datetime import datetime
import numpy as np


class _NumpyEncoder(json.JSONEncoder):
    """Handle numpy types in JSON serialization."""
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        return super().default(obj)


class BaseAgent:
    """Base class for all research agents."""

    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    def think(self, context: str) -> dict:
        """
        Override in subclasses.
        Takes a context string, returns a structured dict with the agent's output.
        """
        raise NotImplementedError

    def log(self, conn, action: str, context: str, result: dict, regime: str = None):
        """Log an agent action to the agent_log table."""
        conn.execute("""
            INSERT INTO agent_log (timestamp, agent_name, action, context, result, regime)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            datetime.now(),
            self.name,
            action,
            context[:1000],  # truncate long context
            json.dumps(result, cls=_NumpyEncoder) if isinstance(result, dict) else str(result),
            regime,
        ])

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name}>"
