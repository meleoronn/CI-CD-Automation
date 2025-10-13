from pathlib import Path
from typing import Optional, Tuple

import httpx
import requests
from git import FetchInfo, GitCommandError, Repo
from git.exc import NoSuchPathError
from git.util import IterableList
from pydantic import HttpUrl

from core.atlassian.auth.strategies import AuthStrategy
from core.atlassian.exceptions import CloneError, PullError, RepositoryError, RepositoryNotFoundError

# TODO put in environment variables
REPO_STORAGE = Path("/home/andrei/workspace/CI-CD-Automation")


class AtlassianClientBase:
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
        if not isinstance(data, dict):
            return "Unexpected error format (not a dict)."

        try:
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


class BitbucketRepositoryClient(AtlassianClientBase):
    def __init__(self, base_url: HttpUrl, credentials: AuthStrategy, workspace: str, repository: str, branch: str):
        super().__init__(base_url=base_url, credentials=credentials)
        self.workspace = workspace
        self.repository = repository
        self.branch = branch

    async def fetch_commits(self, limit: int = 1) -> requests.Response:
        url = f"{self.base_url}/rest/api/1.0/projects/{self.workspace}/repos/{self.repository}/commits"
        params = {"until": f"refs/heads/{self.branch}", "limit": limit}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=self.headers)
            return response

    async def fetch_latest_commit(self) -> requests.Response:
        response = await self.get_repository_commits(limit=1)
        return response


class RepositoryGitClient:
    def __init__(self, clone_url: str, folder: str, credentials: Optional[Tuple[Optional[str], Optional[str]]] = None):
        self.clone_url = clone_url.strip()
        self.folder = folder
        self.credentials = credentials
        self.name = self._compute_name()
        self.path = self._compute_path()
        self.repository: Optional[Repo] = None

    def clone(self, branch: str = "main") -> Repo:
        if self.path.exists():
            raise FileExistsError("A repository with that name already exists.")

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise CloneError(f"Failed to create parent directory '{self.path.parent}': {e}")

        url = self.clone_url

        if not (url.startswith("ssh://") or url.startswith("git@")):
            url = self._authenticated_url()

        try:
            self.repository = Repo.clone_from(
                url=url,
                to_path=self.path,
                branch=branch,
                single_branch=True,
                depth=1,
            )

            if not self.repository:
                raise CloneError("Cloning the repository returned nothing")

            return self.repository
        except GitCommandError as e:
            raise CloneError(f"Git clone failed: {e}")
        except Exception as e:
            raise CloneError(f"Unexpected clone error: {e}")

    def pull(self) -> IterableList[FetchInfo]:
        if not self.path.exists():
            raise FileNotFoundError("The repository was not found.")

        self.repository_load()
        origin = self.repository.remotes.origin

        if not (self.clone_url.startswith("ssh://") or self.clone_url.startswith("git@")):
            origin.set_url(self._authenticated_url())

        try:
            return origin.pull()
        except GitCommandError as e:
            raise PullError(f"Git pull failed: {e}")
        except Exception as e:
            raise PullError(f"Unexpected pull error: {e}")

    def repository_load(self) -> None:
        if self.repository:
            return

        if not self.path.exists():
            raise RepositoryNotFoundError(f"The repository directory was not found at {self.path}")

        try:
            self.repository = Repo(self.path)
        except NoSuchPathError:
            raise RepositoryNotFoundError(f"The repository directory was not found at {self.path}")
        except Exception as e:
            raise RepositoryError(f"Failed to open repository: {e}")

    def _authenticated_url(self) -> str:
        if not self.credentials:
            return self.clone_url

        username, password = self.credentials

        if not username or not password:
            return self.clone_url

        return self.clone_url.replace("https://", f"https://{username}:{password}@")

    def _compute_name(self) -> str:
        return self.clone_url.split("/")[-1].replace(".git", "")

    def _compute_path(self) -> Path:
        return REPO_STORAGE / self.folder
