from typing import Union

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from core.atlassian.api import models
from core.atlassian.auth import auth, strategies
from core.atlassian.service import BitbucketRepositoryClient

router = APIRouter(prefix="/bitbucket/repository", tags=["Bitbucket"])


@router.get(
    "/commits",
    summary="Get commits from a Bitbucket repository branch",
    response_model=models.ResponseBitbucketServerCommits,
    response_model_exclude_none=True,
)
async def get_commits(
    request: models.RequestBitbucketServerCommits = Depends(),
    credentials: Union[strategies.AuthStrategy, JSONResponse] = Depends(auth.get),
) -> Union[models.ResponseBitbucketServerCommits, JSONResponse]:
    if isinstance(credentials, JSONResponse):
        return credentials

    repository = BitbucketRepositoryClient(
        base_url=request.url,
        credentials=credentials,
        project_key=request.workspace,
        repo_slug=request.repository,
        branch_name=request.branch,
    )

    try:
        response = await repository.fetch_commits(limit=request.limit)

        if 200 <= response.status_code <= 299:
            data = response.json()
            message = "The list of commits was successfully received."
            return models.ResponseBitbucketServerCommits(status="success", message=message, data=data)
        elif 400 <= response.status_code <= 499:
            data = response.json()
            message = repository.extract_error(data)
            return JSONResponse(
                content=models.ResponseBitbucketServerCommits(
                    status="error",
                    message=message,
                ).model_dump(exclude_none=True),
                status_code=response.status_code,
            )

        raise Exception("Unexpected response from the Bitbucket server.")
    except Exception as e:
        return JSONResponse(
            content=models.ResponseBitbucketServerCommits(
                status="error",
                message=f"Internal error while fetching commits: {e}",
            ).model_dump(exclude_none=True),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
