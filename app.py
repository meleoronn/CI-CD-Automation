import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import version
from core.atlassian import manager
from core.atlassian.api.router import router as bitbucket_router

print("Starting service...")


def init_application():
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        print("Starting the synchronization of repositories...")
        sync_manager = manager.RepoSyncManager()
        await sync_manager.start_all()
        print("Syncing started")

        try:
            yield
        finally:
            print("Stopping syncing...")

            for t in list(sync_manager.tasks.values()):
                t.cancel()

            await asyncio.sleep(0.2)
            print("All tasks are stopped")

    fastapi_app = FastAPI(
        title="CI/CD Automation",
        summary="CI/CD automation of tracking changes in repositories",
        version=version.__version__,
        # docs_url=None,
        # servers=[{"url": ""}],
        lifespan=lifespan,
    )

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    fastapi_app.include_router(bitbucket_router)
    return fastapi_app


app: FastAPI = init_application()

print("The service is running")
