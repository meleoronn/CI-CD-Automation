from contextlib import contextmanager
from typing import Callable, Generator

from sqlalchemy.orm import Session

from core.db import base


class UnitOfWork:
    """
    The Unit of Work (UoW) pattern.
    Manages the session lifecycle and transaction.
    """

    def __init__(self, session_factory: Callable[[], Session] = base.Session):
        """
        Accepts a factory that creates a Session
        """
        self.session_factory = session_factory

    @contextmanager
    def start(self) -> Generator[Session, None, None]:
        """
        A context manager that opens a session and
        automatically commits or rolls back changes.
        """
        session = self.session_factory()

        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
