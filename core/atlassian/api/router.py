from typing import Union

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from core.atlassian.api import models
from core.atlassian.auth import auth, strategies
from core.atlassian.service import BitbucketServer

router = APIRouter(prefix="/bitbucket/repository", tags=["Bitbucket"])


@router.get(
    "/commits",
    summary="Getting commits from the repository",
    response_model=models.ResponseBitbucketServerCommits,
    response_model_exclude_none=True,
    responses={
        # TODO add examples responses
    },
)
async def test(
    request: models.RequestBitbucketServerCommits = Depends(),
    credentials: Union[strategies.AuthStrategy, HTTPException] = Depends(auth.get_auth),
) -> models.ResponseBitbucketServerCommits:
    try:
        atlassian = BitbucketServer(request.url, credentials)
        response = await atlassian.repository_commits(
            request.workspace,
            request.repository,
            request.branch,
            request.limit,
        )

        if 200 <= response.status_code <= 299:
            data = response.json()
            message = "The list of commits was successfully received."
            return models.ResponseBitbucketServerCommits(status="success", message=message, data=data)
        elif 400 <= response.status_code <= 499:
            data = response.json()
            message = atlassian.extract_error(data)
            return JSONResponse(
                content=models.ResponseBitbucketServerCommits(
                    status="error",
                    message=message,
                ).model_dump(exclude_none=True),
                status_code=response.status_code,
            )

        raise Exception("Unexpected response from the Bitbucket server.")
    except HTTPException as e:
        raise
    except Exception as e:
        return JSONResponse(
            content=models.ResponseBitbucketServerCommits(
                status="error",
                message=f"Internal error when getting a task: {e}",
            ).model_dump(exclude_none=True),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
