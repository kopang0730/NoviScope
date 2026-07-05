from collections.abc import Mapping
from dataclasses import dataclass
from typing import NotRequired, Protocol, TypedDict

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

OPENALEX_WORKS_URL = "https://api.openalex.org/works"
MAX_PAPER_RESULTS = 8
FIVE_YEAR_LOOKBACK = 5


class LiteratureScoutRunError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class OpenAlexQueryParams(TypedDict):
    search: str
    filter: str
    sort: str
    per_page: int
    mailto: NotRequired[str]
    api_key: NotRequired[str]


class OpenAlexAuthor(BaseModel):
    model_config = ConfigDict(frozen=True)
    display_name: str = ""


class OpenAlexAuthorship(BaseModel):
    model_config = ConfigDict(frozen=True)
    author: OpenAlexAuthor | None = None


class OpenAlexSource(BaseModel):
    model_config = ConfigDict(frozen=True)
    display_name: str | None = None
    type: str | None = None


class OpenAlexLocation(BaseModel):
    model_config = ConfigDict(frozen=True)
    landing_page_url: str | None = None
    source: OpenAlexSource | None = None


class OpenAlexWork(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    title: str | None = None
    display_name: str | None = None
    publication_year: int | None = None
    primary_location: OpenAlexLocation | None = None
    doi: str | None = None
    authorships: list[OpenAlexAuthorship] = Field(default_factory=list)
    abstract_inverted_index: dict[str, list[int]] | None = None
    relevance_score: float | None = None
    type: str | None = None


class OpenAlexWorksResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    results: list[OpenAlexWork] = Field(default_factory=list)


class OpenAlexHTTPClient(Protocol):
    def get(
        self,
        url: str,
        *,
        params: Mapping[str, str | int],
        headers: Mapping[str, str],
    ) -> httpx.Response: ...


class OpenAlexSearchClient(Protocol):
    def search(self, query: str, *, current_year: int) -> list[OpenAlexWork]: ...


@dataclass(frozen=True, slots=True)
class OpenAlexClientConfig:
    api_key: SecretStr | None = None
    email: str | None = None
    works_url: str = OPENALEX_WORKS_URL


@dataclass(frozen=True, slots=True)
class OpenAlexWorksClient:
    config: OpenAlexClientConfig
    http_client: OpenAlexHTTPClient | None = None

    def search(self, query: str, *, current_year: int) -> list[OpenAlexWork]:
        api_key = openalex_api_key_value(self.config)
        if api_key is None:
            raise LiteratureScoutRunError(
                "Configure NOVISCOPE_OPENALEX_API_KEY before running Literature Scout."
            )
        params: OpenAlexQueryParams = {
            "filter": f"from_publication_date:{current_year - FIVE_YEAR_LOOKBACK}-01-01",
            "per_page": MAX_PAPER_RESULTS,
            "search": query,
            "sort": "relevance_score:desc",
        }
        if self.config.email:
            params["mailto"] = self.config.email
        params["api_key"] = api_key
        try:
            response = self._get(params)
            response.raise_for_status()
            return OpenAlexWorksResponse.model_validate(response.json()).results
        except httpx.HTTPStatusError as exc:
            raise LiteratureScoutRunError(
                f"OpenAlex request failed with HTTP status {exc.response.status_code}."
            ) from exc
        except httpx.RequestError as exc:
            raise LiteratureScoutRunError(
                "OpenAlex request failed before a response was received."
            ) from exc
        except (ValueError, ValidationError) as exc:
            raise LiteratureScoutRunError("OpenAlex returned an invalid works response.") from exc

    def _get(self, params: OpenAlexQueryParams) -> httpx.Response:
        headers = {"User-Agent": "NoviScope/0.1"}
        if self.config.email:
            headers["User-Agent"] = f"NoviScope/0.1 (mailto:{self.config.email})"
        if self.http_client is not None:
            return self.http_client.get(self.config.works_url, params=params, headers=headers)
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            return client.get(self.config.works_url, params=params, headers=headers)


def openalex_api_key_value(config: OpenAlexClientConfig) -> str | None:
    if config.api_key is None:
        return None
    api_key = config.api_key.get_secret_value().strip()
    return api_key or None
