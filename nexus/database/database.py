"""SQLAlchemy-managed SQLite connections when installed; stdlib fallback otherwise."""
import sqlite3
def connect(path):
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.pool import NullPool
    except ImportError:
        return sqlite3.connect(path,check_same_thread=False),None,None,"sqlite3 offline fallback"
    url="sqlite+pysqlite:///:memory:" if path==":memory:" else "sqlite+pysqlite:///"+path.replace("\\","/")
    engine=create_engine(url,connect_args={"check_same_thread":False},poolclass=NullPool)
    proxy=engine.raw_connection()
    return proxy.driver_connection,engine,proxy,"SQLAlchemy-managed SQLite"

