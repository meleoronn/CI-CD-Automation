from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBasic, HTTPBasicCredentials, HTTPBearer

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


def get_auth(
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    basic: Optional[HTTPBasicCredentials] = Depends(basic_scheme),
) -> AuthStrategy:
    if bearer:
        return BearerAuth(bearer.credentials)
    elif basic:
        return BasicAuth(basic.username, basic.password)

    raise HTTPException(status_code=401, detail="Check the entered username and password.")
