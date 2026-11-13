from nexus.database.repository import Repository
from nexus.service import bootstrap

def fixture():
    repo=Repository(":memory:")
    bootstrap(repo)
    return repo

