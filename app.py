from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import version

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

    return fastapi_app


app: FastAPI = init_application()


@app.get("/ping")
async def ping():
    return "pong"


print("The service is running")
