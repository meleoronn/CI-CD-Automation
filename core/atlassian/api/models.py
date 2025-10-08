from pydantic import BaseModel, Field, HttpUrl


# TODO test model
class JiraCreateIssueRequest(BaseModel):
    app_url: HttpUrl = Field(...)
    workspace: str = Field(...)
    repo: str = Field(...)
    branch: str = Field(...)
    limit: int = Field(...)
