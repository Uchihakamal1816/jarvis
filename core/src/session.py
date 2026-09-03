"""
JARVIS Core — Session Management
Tracks the state of a user's interaction with JARVIS.
"""

from __future__ import annotations
import uuid
import time
from typing import Any, Dict, List

class Session:
    def __init__(self, session_id: str | None = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.created_at = time.time()
        self.history: List[Dict[str, Any]] = []
        self.context: Dict[str, Any] = {}
        
    def add_interaction(self, role: str, content: str) -> None:
        """Add a message to the session history."""
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        
    def get_history(self) -> List[Dict[str, Any]]:
        return self.history
        
    def update_context(self, key: str, value: Any) -> None:
        """Update the session context with specific state variables."""
        self.context[key] = value

class SessionManager:
    """Manages active sessions."""
    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        
    def get_or_create_session(self, session_id: str | None = None) -> Session:
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]
        
        new_session = Session(session_id)
        self._sessions[new_session.session_id] = new_session
        return new_session

# Global instance for basic app state
session_manager = SessionManager()
