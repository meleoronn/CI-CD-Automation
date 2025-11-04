import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Optional

from core.atlassian.service import RepositoryGitClient
from core.db.models import Repository, RepoStatus, SyncStatus
from core.db.repositories import RepositoryReadWrite
from core.db.unit_of_work import UnitOfWork


class RepoSyncManager:
    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()
        self.uow = UnitOfWork()

    async def start_all(self):
        with self.uow.start() as session:
            query = session.query(Repository).filter(
                Repository.status == RepoStatus.active,
                Repository.active.is_(True),
                Repository.auto_sync.is_(True),
            )
            repositories = [(r.id, r.name) for r in query.all()]

        for repo_id, repo_name in repositories:
            await self.start(repo_id)

    async def start(self, repository_id: str):
        async with self._global_lock:
            task = self._tasks.get(repository_id)

            if task and not task.done():
                return

            self._locks.setdefault(repository_id, asyncio.Lock())
            task = asyncio.create_task(self._poll_loop(repository_id))
            self._tasks[repository_id] = task

    async def stop(self, repository_id: str):
        async with self._global_lock:
            task = self._tasks.pop(repository_id, None)

            if task:
                task.cancel()

    async def restart(self, repository_id: str):
        await self.stop(repository_id)
        await self.start(repository_id)

    async def _poll_loop(self, repository_id: str):
        try:
            while True:
                with self.uow.start() as session:
                    db = RepositoryReadWrite(session)
                    db_repository = db.get_by_id(repository_id)

                    if not db_repository:
                        break

                    if (
                        db_repository.status != RepoStatus.active
                        or not db_repository.active
                        or not db_repository.enable_polling
                    ):
                        break

                    interval = sync_interval_to_seconds(db_repository.sync_interval)

                lock = self._locks.setdefault(repository_id, asyncio.Lock())

                async with lock:
                    await asyncio.to_thread(self._do_sync, repository_id)

                await asyncio.sleep(interval)
        except asyncio.CancelledError as e:
            return
        except Exception as e:
            return

    def _do_sync(self, repository_id: str):
        with self.uow.start() as session:
            db = RepositoryReadWrite(session)
            db_repository = db.get_by_id(repository_id)
            db_repository.last_sync_status = SyncStatus.in_progress
            db_repository.last_sync_at = datetime.now(timezone.utc)

            max_retries = int(db_repository.max_retries or 3)
            retry_delay = float((db_repository.retry_delay or 1000) / 1000.0)
            name = db_repository.name
            session.commit()

        client = RepositoryGitClient(folder=name)

        for attempt in range(1, max_retries + 1):
            try:
                client.pull()
                break
            except Exception:
                attempt += 1

                if attempt < max_retries:
                    time.sleep(retry_delay)


def sync_interval_to_seconds(raw: Optional[int]) -> float:
    if raw is None:
        return 30.0

    return float(raw) / 1000.0 if raw >= 1000 else float(raw)
