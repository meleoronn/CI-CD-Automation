import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.atlassian.service import RepositoryGitClient
from core.db.models import Repository, RepoStatus, SyncStatus
from core.db.repositories import RepositoryReadWrite
from core.db.unit_of_work import UnitOfWork


def sync_interval_to_seconds(raw: Optional[int]) -> float:
    if raw is None:
        return 30.0

    return float(raw) / 1000.0 if raw >= 1000 else float(raw)


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
                Repository.enable_polling.is_(True),
                Repository.auto_sync.is_(True),
            )
            repositories = [(str(r.id), r.name) for r in query.all()]

        for repository_id, repository_name in repositories:
            await self.start(repository_name, repository_id)

    async def start(self, repository_name: str, repository_id: Optional[str] = None):
        async with self._global_lock:
            task = self._tasks.get(repository_id)

            if task and not task.done():
                print(f"[{repository_id}] Task already running — skip start.")
                return

            if repository_id is None:
                with self.uow.start() as session:
                    db = RepositoryReadWrite(session)
                    db_repository = db.get_by_name(repository_name)

                    if not db_repository:
                        print(f"[{repository_name}] Cannot start: repository not found in DB.")
                        return

                    repository_id = db_repository.id

            self._locks.setdefault(repository_id, asyncio.Lock())

            task = asyncio.create_task(self._poll_loop(repository_id, repository_name))
            self._tasks[repository_id] = task
            print(f"[{repository_id}] Started polling task for repository '{repository_name}'.")

    async def stop(self, repository_id: str):
        async with self._global_lock:
            task = self._tasks.pop(repository_id, None)

            if task:
                task.cancel()

    async def restart(self, repository_id: str):
        await self.stop(repository_id)
        await self.start(repository_id)

    async def _poll_loop(self, repository_id: str, repository_name: str):
        try:
            while True:
                print(f"[{repository_id}] Checking repository '{repository_name}' for updates...")

                with self.uow.start() as session:
                    db = RepositoryReadWrite(session)
                    db_repository = db.get_by_id(repository_id)

                    if not db_repository:
                        print(f"[{repository_id}] Repository record not found in DB — stopping polling loop.")
                        break

                    if db_repository.status != RepoStatus.active or not db_repository.active:
                        print(f"[{repository_id}] Repository is not active — stopping polling loop.")
                        break

                    if not db_repository.enable_polling:
                        print(f"[{repository_id}] Polling disabled for repository — stopping polling loop.")
                        break

                    if not db_repository.auto_sync:
                        print(f"[{repository_id}] Auto-sync disabled for repository — stopping polling loop.")
                        break

                    interval = sync_interval_to_seconds(db_repository.sync_interval)

                lock = self._locks.setdefault(repository_id, asyncio.Lock())

                async with lock:
                    print(f"[{repository_id}] Starting synchronization (blocking work will run in a thread)...")
                    await asyncio.to_thread(self._do_sync, repository_id, repository_name)

                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            print(f"[{repository_id}] Polling task was cancelled.")
            raise
        except Exception as e:
            print(f"[{repository_id}] Polling loop exited with error: {e}")

    def _do_sync(self, repository_id: str, repository_name: str):
        client = RepositoryGitClient(folder=repository_name)

        if client.relevance():
            print(f"[{repository_id}] There are no changes for the repository")
            return

        with self.uow.start() as session:
            db = RepositoryReadWrite(session)
            db_repository = db.get_by_id(repository_id)

            db_repository.last_sync_status = SyncStatus.in_progress
            db_repository.last_sync_at = datetime.now(timezone.utc)

            max_retries = int(db_repository.max_retries or 3)
            retry_delay = float((db_repository.retry_delay or 1000) / 1000.0)
            session.commit()

        for attempt in range(1, max_retries + 1):
            try:
                print(f"[{repository_id}] There are changes, pooling")
                client.pull()
                return
            except Exception:
                attempt += 1

                if attempt < max_retries:
                    time.sleep(retry_delay)

    @property
    def tasks(self):
        return self._tasks
