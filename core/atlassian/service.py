import shutil
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import httpx
import requests
from git import FetchInfo, GitCommandError, Repo
from git.exc import NoSuchPathError
from git.util import IterableList
from pydantic import HttpUrl

from core.atlassian.auth.strategies import AuthStrategy
from core.db.models import Repository
from core.db.repositories import RepositoryReadWrite
from core.db.unit_of_work import UnitOfWork
from core.settings import setting


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

        return None

    async def fetch_latest_commit(self) -> requests.Response:
        response = await self.get_repository_commits(limit=1)
        return response

    @staticmethod
    def provider_info(base_url) -> dict:
        url = f"{base_url}/rest/api/1.0/application-properties"
        response = requests.get(url, timeout=10.0)
        data = response.json()

        provider_name = data.get("displayName", "Unknown name")
        provider_name += " Server"
        provider_version = data.get("version", "")
        data["provider"] = f"{provider_name} {provider_version}"
        return data


class RepositoryGitClient:
    def __init__(self, folder: str, credentials: Optional[Tuple[Optional[str], Optional[str]]] = None):
        self.folder = folder
        self.credentials = credentials
        self.path = Path(setting.REPOSITORIES_STORAGE) / self.folder
        self.repository: Optional[Repo] = None
        self.uow = UnitOfWork()

    def clone(self, url: str, branch: str = "main") -> Repo:
        if self.path.exists():
            raise FileExistsError("A repository with that name already exists.")

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise Exception(f"Failed to create parent directory '{self.path.parent}': {e}")

        try:
            base_url = self._compute_base_url(url, filter_path=["bitbucket"])
            provider_data = BitbucketRepositoryClient.provider_info(base_url)
            provider_name = provider_data.get("provider", "Unknown")
        except Exception as e:
            raise Exception(f"Error getting basic repository information: {e}")

        clone_url = url

        if self._needs_authentication(url):
            clone_url = self._create_authenticated_url(url)

        try:
            self.repository = Repo.clone_from(
                url=clone_url,
                to_path=self.path,
                branch=branch,
                single_branch=True,
                depth=1,
            )

            if not self.repository:
                raise Exception("Cloning the repository returned nothing")

            try:
                commit = self.repository.head.commit

                with self.uow.start() as session:
                    db = RepositoryReadWrite(session)
                    db_repository = Repository(
                        name=self.folder,
                        provider=provider_name,
                        api_url=base_url,
                        clone_url=url,
                        branch=branch,
                        last_commit_hash=commit.hexsha,
                        last_commit_message=commit.message.strip(),
                        last_commit_author=str(commit.author),
                        last_commit_timestamp=commit.authored_datetime.isoformat(),
                    )
                    db.add(db_repository)
            except Exception:
                self.delete()
                raise

            return self.repository
        except GitCommandError as e:
            raise Exception(f"Git clone failed: {e}")
        except Exception as e:
            raise Exception(f"Unexpected clone error: {e}")

    def pull(self, clone_url: Optional[str] = None) -> IterableList[FetchInfo]:
        if not self.path.exists():
            raise FileNotFoundError("The repository was not found.")

        self.repository_load()

        try:
            origin = self.repository.remotes.origin

            if clone_url and self._needs_authentication(clone_url):
                origin.set_url(self._create_authenticated_url(clone_url))

            return origin.pull()
        except GitCommandError as e:
            raise Exception(f"Git pull failed: {e}")
        except Exception as e:
            raise Exception(f"Unexpected pull error: {e}")

    def delete(self):
        if not self.path.exists():
            raise FileNotFoundError("The repository was not found.")

        if hasattr(self, "repository") and self.repository is not None:
            try:
                self.repository.close()
            except Exception:
                pass
            finally:
                self.repository = None

        try:
            shutil.rmtree(self.path)
        except OSError as e:
            raise OSError(f"Failed to delete repository directory: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during repository deletion: {e}")

    def repository_load(self) -> Repo:
        if self.repository:
            return self.repository

        try:
            self.repository = Repo(self.path)
            return self.repository
        except NoSuchPathError:
            raise Exception(f"The repository directory was not found at {self.path}")
        except Exception as e:
            raise Exception(f"Failed to open repository: {e}")

    def _create_authenticated_url(self, clone_url: str) -> str:
        if not self.credentials:
            return clone_url

        username, password = self.credentials

        if not username or not password:
            return clone_url

        return clone_url.replace("https://", f"https://{username}:{password}@")

    @staticmethod
    def _needs_authentication(clone_url: str) -> bool:
        return not clone_url.startswith(("ssh://", "git@"))

    @staticmethod
    def _compute_base_url(clone_url: str, filter_path: List[str] = None) -> str:
        parsed = urlparse(clone_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        if filter_path:
            path_parts = parsed.path.split("/")

            if len(path_parts) > 1 and path_parts[1] in filter_path:
                context_path = "/" + path_parts[1]
                base_url += context_path

        return base_url

    # @staticmethod
    # def _compute_name(self, clone_url: str) -> str:
    #     return clone_url.split("/")[-1].replace(".git", "")
