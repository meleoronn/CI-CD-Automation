from typing import Union

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from core.atlassian.api import models
from core.atlassian.auth import auth, strategies
from core.atlassian.service import BitbucketRepositoryClient, RepositoryGitClient

router = APIRouter(prefix="/bitbucket/repository", tags=["Bitbucket"])


@router.get(
    "/commits",
    summary="Get commits from a Bitbucket repository branch",
    response_model=models.BitbucketServerResponse,
    response_model_exclude_none=True,
)
async def get_commits(
    request: models.RequestBitbucketServerCommits = Depends(),
    credentials: Union[strategies.AuthStrategy, JSONResponse] = Depends(auth.bitbucket),
) -> Union[models.BitbucketServerResponse, JSONResponse]:
    if isinstance(credentials, JSONResponse):
        return credentials

    repository = BitbucketRepositoryClient(
        base_url=request.url,
        credentials=credentials,
        workspace=request.workspace,
        repository=request.repository,
        branch=request.branch,
    )

    try:
        response = await repository.fetch_commits(limit=request.limit)
        data = response.json()

        if 200 <= response.status_code <= 299:
            message = "The list of commits was successfully received."
            return models.BitbucketServerResponse(status="success", message=message, data=data)
        elif 400 <= response.status_code <= 499:
            message = repository.extract_error(data)
            return JSONResponse(
                content=models.BitbucketServerResponse(
                    status="error",
                    message=message,
                ).model_dump(exclude_none=True),
                status_code=response.status_code,
            )

        raise Exception("Unexpected response from the Bitbucket server.")
    except Exception as e:
        return JSONResponse(
            content=models.BitbucketServerResponse(
                status="error",
                message=f"Internal error while fetching commits: {e}",
            ).model_dump(exclude_none=True),
            status_code=500,
        )


@router.post(
    "/clone",
    summary="Cloning a repository",
    response_model=models.BitbucketServerResponse,
    response_model_exclude_none=True,
)
async def clone(
    request: models.RepositoryCloneRequest,
    credentials: Union[strategies.AuthStrategy, JSONResponse] = Depends(auth.git),
) -> Union[models.BitbucketServerResponse, JSONResponse]:
    client = RepositoryGitClient(clone_url=request.url, folder=request.name, credentials=credentials)

    try:
        client.clone(branch=request.branch)
        return {"status": "success", "message": "The repository is cloned"}
    except FileExistsError as e:
        return JSONResponse(
            content=models.BitbucketServerResponse(
                status="error",
                message=str(e),
            ).model_dump(exclude_none=True),
            status_code=400,
        )
    except Exception as e:
        return JSONResponse(
            content=models.BitbucketServerResponse(
                status="error",
                message=f"Internal error when cloning the repository: {e}",
            ).model_dump(exclude_none=True),
            status_code=500,
        )


@router.put(
    "/pull",
    summary="Pulling up repository changes",
    response_model=models.BitbucketServerResponse,
    response_model_exclude_none=True,
)
async def pull(
    request: models.RepositoryPullRequest,
    credentials: Union[strategies.AuthStrategy, JSONResponse] = Depends(auth.git),
) -> Union[models.BitbucketServerResponse, JSONResponse]:
    client = RepositoryGitClient(clone_url=request.url, folder=request.name, credentials=credentials)

    try:
        client.pull()
        return {"status": "success", "message": "The changes were pulled from the repository"}
    except FileNotFoundError as e:
        return JSONResponse(
            content=models.BitbucketServerResponse(
                status="error",
                message=str(e),
            ).model_dump(exclude_none=True),
            status_code=400,
        )
    except Exception as e:
        return JSONResponse(
            content=models.BitbucketServerResponse(
                status="error",
                message=f"Internal error when extracting changes from the repository: {e}",
            ).model_dump(exclude_none=True),
            status_code=500,
        )
