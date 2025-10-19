from contextlib import contextmanager

from core.db.base import SessionLocal


class UnitOfWork:
    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    @contextmanager
    def start(self):
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
