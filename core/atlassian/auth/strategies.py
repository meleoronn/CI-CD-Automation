import base64
from abc import ABC, abstractmethod
from typing import Dict


class AuthStrategy(ABC):
    @abstractmethod
    def get_headers(self) -> Dict[str, str]:
        pass


class BearerAuth(AuthStrategy):
    def __init__(self, token: str):
        self.token = token

    def get_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


class BasicAuth(AuthStrategy):
    def __init__(self, username: str, password: str):
        credentials = f"{username}:{password}"
        self.encoded = base64.b64encode(credentials.encode()).decode()

    def get_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Basic {self.encoded}"}
