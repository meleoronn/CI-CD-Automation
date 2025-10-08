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


#TODO test class
class AtlassianBitbucketServer(AtlassianBase):
    def get_commits(self, workspace, repo, branch, limit) -> requests.Response:
        url = f"{self.base_url}/rest/api/1.0/projects/{workspace}/repos/{repo}/commits"
        params = {
            "until": f"refs/heads/{branch}",
            "limit": limit,
        }

        print("START get commits...\n")

        response = requests.get(url, params=params, headers=self.headers)

        print("STATUS CODE", response.status_code, "\n")
        print("RESPONSE TEXT", response.text, "\n")
        print("REPONSE JSON", response.json(), "\n")
        return response.json()
