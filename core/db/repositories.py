from typing import List, Optional

from sqlalchemy.future import select
from sqlalchemy.orm import Session

from core.db.models import Repository


class RepositoryReadWrite:
    """
    Data Access Layer for the Repository model.
    """

    def __init__(self, session: Session):
        """
        Initializing the repository with the SQLAlchemy session.
        The session is created in UnitOfWork and transferred here.
        """
        self.session: Session = session

    def add(self, repository: Repository) -> None:
        """
        Adds a new Repository object to the current session.
        The commit will only occur when UnitOfWork is called.
        """
        self.session.add(repository)

    def get_by_id(self, repository_id: str) -> Optional[Repository]:
        """
        Returns the repository by ID or None if not found.
        """
        statement = select(Repository).where(Repository.id == repository_id)
        return self.session.execute(statement).scalars().first()

    def get_for_pulling(self, limit: int = 100) -> List[Repository]:
        """
        Retrieves the list of active repositories to be polled.
        """
        statement = (
            select(Repository)
            .where(Repository.active.is_(True))
            .where(Repository.enable_polling.is_(True))
            .order_by(Repository.last_sync_at.asc().nullsfirst())
            .limit(limit)
        )
        return list(self.session.execute(statement).scalars().all())

    def update_commit_info(
        self, repository: Repository, commit_hash: str, message: str, author: str, committed_at
    ) -> Repository:
        """
        Updates the data of the last commit in the repository.
        """
        repository.last_commit_hash = commit_hash
        repository.last_commit_message = message
        repository.last_commit_author = author
        repository.last_commit_timestamp = committed_at
        repository.sync_count = (repository.sync_count or 0) + 1
        return repository
