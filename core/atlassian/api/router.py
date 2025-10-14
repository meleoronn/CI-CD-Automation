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
        message = f"Internal error while fetching commits: {e}"
        status_code = 500

    content = models.BitbucketServerResponse(status="error", message=message).model_dump(exclude_none=True)
    return JSONResponse(content=content, status_code=status_code)


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
    try:
        client = RepositoryGitClient(folder=request.name, credentials=credentials)
        client.clone(clone_url=request.url, branch=request.branch)
        return {"status": "success", "message": "The repository is cloned"}
    except FileExistsError as e:
        message = str(e)
        status_code = 400
    except Exception as e:
        message = f"Internal error when cloning the repository: {e}"
        status_code = 500

    content = models.BitbucketServerResponse(status="error", message=message).model_dump(exclude_none=True)
    return JSONResponse(content=content, status_code=status_code)


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
    try:
        client = RepositoryGitClient(folder=request.name, credentials=credentials)
        client.pull()
        return {"status": "success", "message": "The changes were pulled from the repository"}
    except FileNotFoundError as e:
        message = str(e)
        status_code = 404
    except Exception as e:
        message = f"Internal error when extracting changes from the repository: {e}"
        status_code = 500

    content = models.BitbucketServerResponse(status="error", message=message).model_dump(exclude_none=True)
    return JSONResponse(content=content, status_code=status_code)


@router.delete(
    "/delete",
    summary="Deleting a cloned repository",
    response_model=models.BitbucketServerResponse,
    response_model_exclude_none=True,
)
async def pull(
    request: models.RepositoryDeleteRequest,
    credentials: Union[strategies.AuthStrategy, JSONResponse] = Depends(auth.git),
) -> Union[models.BitbucketServerResponse, JSONResponse]:
    try:
        client = RepositoryGitClient(folder=request.name, credentials=credentials)
        client.delete()
        return {"status": "success", "message": "The cloned repository has been deleted"}
    except FileNotFoundError as e:
        message = str(e)
        status_code = 404
    except Exception as e:
        message = f"Internal error when deleting a cloned repository: {e}"
        status_code = 500

    content = models.BitbucketServerResponse(status="error", message=message).model_dump(exclude_none=True)
    return JSONResponse(content=content, status_code=status_code)
