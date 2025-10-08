from typing import Union

from fastapi import APIRouter, Depends, HTTPException

from core.atlassian.api.models import JiraCreateIssueRequest
from core.atlassian.auth import auth, strategies
from core.atlassian.service import AtlassianBitbucketServer

router = APIRouter(prefix="", tags=[""])


# TODO test route
@router.get("/test")
async def test(
    request: JiraCreateIssueRequest = Depends(),
    credentials: Union[strategies.AuthStrategy, HTTPException] = Depends(auth.get_auth),
):
    atlassian = AtlassianBitbucketServer(request.app_url, credentials)
    return atlassian.get_commits(request.workspace, request.repo, request.branch, request.limit)
