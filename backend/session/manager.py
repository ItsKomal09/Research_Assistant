from typing import List, Dict
import uuid
import logging

logger = logging.getLogger(__name__)

# in-memory store: { session_id: [ {role, content}, ... ] }
_sessions: Dict[str, List[dict]] = {}


def create_session() -> str:
    """Generate a new session ID."""
    session_id = str(uuid.uuid4())
    _sessions[session_id] = []
    logger.info(f"Created session: {session_id}")
    return session_id


def get_history(session_id: str) -> List[dict]:
    """Get chat history for a session. Returns empty list if not found."""
    return _sessions.get(session_id, [])


def add_message(session_id: str, role: str, content: str) -> None:
    """Append a message to a session's history."""
    if session_id not in _sessions:
        _sessions[session_id] = []
    _sessions[session_id].append({"role": role, "content": content})


def session_exists(session_id: str) -> bool:
    return session_id in _sessions


def clear_session(session_id: str) -> bool:
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False


def list_sessions() -> List[str]:
    return list(_sessions.keys())