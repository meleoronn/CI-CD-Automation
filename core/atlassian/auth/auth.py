from typing import Optional, Union

from fastapi import Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBasic, HTTPBasicCredentials, HTTPBearer

from core.atlassian.api import models
from core.atlassian.auth.strategies import AuthStrategy, BasicAuth, BearerAuth

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description="Bearer token authorization scheme. Has higher priority over Basic Auth.",
)

basic_scheme = HTTPBasic(
    auto_error=False,
    scheme_name="BasicAuth",
    description="Basic HTTP authentication with username and password.",
)


def get(
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    basic: Optional[HTTPBasicCredentials] = Depends(basic_scheme),
) -> Union[AuthStrategy, JSONResponse]:
    if bearer:
        return BearerAuth(bearer.credentials)
    elif basic:
        return BasicAuth(basic.username, basic.password)

    return JSONResponse(
        content=models.ResponseBitbucketServerCommits(
            status="error",
            message="Check the entered username and password.",
        ).model_dump(exclude_none=True),
        status_code=401,
    )
