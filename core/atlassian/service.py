import httpx
import requests
from pydantic import HttpUrl

from core.atlassian.auth.strategies import AuthStrategy


class AtlassianBase:
    def __init__(self, base_url: HttpUrl, credentials: AuthStrategy):
        self.base_url = base_url
        self.credentials = credentials
        self._headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            **self.credentials.get_headers(),
        }

    @property
    def headers(self):
        return self._headers.copy()

    @staticmethod
    def extract_error(data: dict) -> str:
        try:
            if not isinstance(data, dict):
                return "Unexpected error format (not a dict)."

            if "errors" in data and isinstance(data["errors"], list):
                return str(data["errors"][0].get("message", "The returned message was not found."))
            elif "message" in data and isinstance(data["errors"], str):
                return str(data.get("message", "The returned message was not found."))
            elif "errorMessages" in data and isinstance(data["errorMessages"], list):
                return str(data["errorMessages"][0])
            else:
                return "The error cannot be handled."

        except Exception as e:
            return f"Error extracting error message: {e}"


class BitbucketServer(AtlassianBase):
    async def repository_commits(
        self, workspace: str, repository: str, branch: str, limit: int = 1
    ) -> requests.Response:
        url = f"{self.base_url}/rest/api/1.0/projects/{workspace}/repos/{repository}/commits"
        params = {"until": f"refs/heads/{branch}", "limit": limit}

        async with httpx.AsyncClient(params=params, headers=self.headers) as client:
            return await client.get(url)
