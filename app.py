from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import version
from core.atlassian.api.router import router as bitbucket_router

print("Starting service...")


def init_application():
    fastapi_app = FastAPI(
        title="CI/CD Automation",
        summary="CI/CD automation of tracking changes in repositories",
        version=version.__version__,
        # docs_url=None,
        # servers=[{"url": ""}],
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
