from typing import Union

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl

import version
from core.atlassian.api import AtlassianBitbucketServer
from core.atlassian.auth.auth import get_auth
from core.atlassian.auth.strategies import AuthStrategy

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


#TODO test model
class JiraCreateIssueRequest(BaseModel):
    app_url: HttpUrl = Field(...)
    workspace: str = Field(...)
    repo: str = Field(...)
    branch: str = Field(...)
    limit: int = Field(...)



#TODO test route
@app.get("/test")
async def test(
    request: JiraCreateIssueRequest = Depends(),
    credentials: Union[AuthStrategy, HTTPException] = Depends(get_auth),
):
    atlassian = AtlassianBitbucketServer(request.app_url, credentials)
    return atlassian.get_commits(request.workspace, request.repo, request.branch, request.limit)


print("The service is running")
