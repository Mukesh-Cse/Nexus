"""Session-isolated repositories for an anonymous public demo."""
from nexus.database.repository import Repository
from nexus.service import bootstrap

def session_repository(state):
    """Caller supplies session-local state, never a globally cached dictionary."""
    key="_nexus_session_repository"
    if key not in state:
        repo=Repository(":memory:")
        bootstrap(repo)
        state[key]=repo
    return state[key]

