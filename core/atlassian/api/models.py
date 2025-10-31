from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class BitbucketServerBase(BaseModel):
    url: HttpUrl = Field(..., description="Atlassian host with the bitbucket server that is being accessed")


class BitbucketWorkspace(BitbucketServerBase):
    workspace: str = Field(..., min_length=1, description="Workspace identifier")


class BitbucketRepository(BitbucketWorkspace):
    repository: str = Field(..., min_length=1, description="Repository name")


class RequestBitbucketServerCommits(BitbucketRepository):
    branch: str = Field(..., min_length=1, description="Repository branch")
    limit: int = Field(default=1, ge=1, le=25, description="How many results to return per page")


class RepositoryRequest(BaseModel):
    name: str = Field(..., min_length=1, description="The unique name under which the repository will be saved")


class RepositoryCloneRequest(RepositoryRequest):
    url: str = Field(..., min_length=1, description="The link for cloning the repository")
    branch: str = Field(default="main", min_length=1, description="The branch that needs to be cloned or updated")


class RepositoryPullRequest(RepositoryRequest):
    pass


class RepositoryDeleteRequest(RepositoryRequest):
    pass


class RepositoryRelevanceRequest(RepositoryRequest):
    pass


class ResponseStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


class BaseResponse(BaseModel):
    status: ResponseStatus = Field(..., description="Request status")
    message: str = Field(..., description="The output message")


class BitbucketServerResponse(BaseResponse):
    data: Optional[dict] = Field(None, description="List of commits")

    class Config:
        use_enum_values = True
