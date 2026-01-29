"""ESI Client with rate limiting, caching, and OAuth support."""

import asyncio
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.app.core.config import settings

# ESI Configuration
ESI_BASE_URL = settings.ESI_BASE_URL
ESI_OAUTH_URL = "https://login.eveonline.com/v2/oauth"
ESI_DATASOURCE = "tranquility"

# Rate limiting - use settings with fallback defaults
DEFAULT_CONCURRENCY = settings.ESI_CONCURRENCY_LIMIT
DEFAULT_TIMEOUT = settings.ESI_TIMEOUT
ERROR_LIMIT_REMAIN_THRESHOLD = 20  # Slow down when this many errors remain


class ESIError(Exception):
    """Base ESI error."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ESIRateLimitError(ESIError):
    """Rate limit exceeded."""

    pass


class ESIServerError(ESIError):
    """ESI server error (5xx)."""

    pass


class ESIAuthError(ESIError):
    """Authentication error."""

    pass


class TokenData(BaseModel):
    """OAuth token data."""

    access_token: str
    refresh_token: str
    expires_at: datetime
    character_id: int
    character_name: str
    scopes: list[str]


class ESIClient:
    """Async ESI client with rate limiting and caching.

    Features:
    - Automatic retry with exponential backoff
    - Respects ESI error limit headers
    - Per-endpoint TTL caching
    - OAuth2 token refresh
    """

    def __init__(
        self,
        concurrency: int = DEFAULT_CONCURRENCY,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.semaphore = asyncio.Semaphore(concurrency)
        self.timeout = timeout
        self.client: httpx.AsyncClient | None = None
        self._error_limit_remain = 100
        self._error_limit_reset: datetime | None = None
        self._token: TokenData | None = None

    async def __aenter__(self) -> "ESIClient":
        self.client = httpx.AsyncClient(
            base_url=ESI_BASE_URL,
            timeout=self.timeout,
            headers={
                "Accept": "application/json",
                "User-Agent": "EVE-Starmap/0.1.0 (github.com/AreteDriver/Sentinel-)",
            },
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self.client:
            await self.client.aclose()

    def _update_error_limits(self, response: httpx.Response) -> None:
        """Update error limit tracking from response headers."""
        remain = response.headers.get("x-esi-error-limit-remain")
        reset = response.headers.get("x-esi-error-limit-reset")

        if remain is not None:
            self._error_limit_remain = int(remain)
        if reset is not None:
            self._error_limit_reset = datetime.utcnow() + timedelta(seconds=int(reset))

    async def _wait_if_rate_limited(self) -> None:
        """Wait if we're approaching the error limit."""
        if self._error_limit_remain < ERROR_LIMIT_REMAIN_THRESHOLD:
            if self._error_limit_reset:
                wait_seconds = (self._error_limit_reset - datetime.utcnow()).total_seconds()
                if wait_seconds > 0:
                    await asyncio.sleep(min(wait_seconds, 60))

    @retry(
        retry=retry_if_exception_type((ESIServerError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=30),
    )
    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        authenticated: bool = False,
    ) -> tuple[Any, dict[str, str]]:
        """Make a GET request to ESI.

        Args:
            endpoint: API endpoint (e.g., "/universe/systems/")
            params: Query parameters
            authenticated: Whether to include auth token

        Returns:
            Tuple of (response_data, cache_headers)
        """
        await self._wait_if_rate_limited()

        async with self.semaphore:
            if not self.client:
                raise RuntimeError("Client not initialized")

            # Build request params
            request_params = {"datasource": ESI_DATASOURCE}
            if params:
                request_params.update(params)

            # Add auth header if needed
            headers = {}
            if authenticated and self._token:
                await self._ensure_token_valid()
                headers["Authorization"] = f"Bearer {self._token.access_token}"

            response = await self.client.get(endpoint, params=request_params, headers=headers)
            self._update_error_limits(response)

            # Handle errors
            if response.status_code == 420:
                raise ESIRateLimitError(
                    "ESI error limit exceeded",
                    status_code=420,
                )
            if response.status_code == 401:
                raise ESIAuthError(
                    "Authentication required or token expired",
                    status_code=401,
                )
            if response.status_code >= 500:
                raise ESIServerError(
                    f"ESI server error: {response.status_code}",
                    status_code=response.status_code,
                )

            response.raise_for_status()

            # Extract cache headers
            cache_headers = {
                "etag": response.headers.get("etag", ""),
                "expires": response.headers.get("expires", ""),
                "last-modified": response.headers.get("last-modified", ""),
            }

            return response.json(), cache_headers

    async def get_paginated(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        authenticated: bool = False,
    ) -> list[Any]:
        """Fetch all pages of a paginated endpoint.

        Args:
            endpoint: API endpoint
            params: Query parameters
            authenticated: Whether to include auth token

        Returns:
            Combined list of all items from all pages
        """
        all_items = []
        page = 1

        while True:
            page_params = {"page": page}
            if params:
                page_params.update(params)

            data, headers = await self.get(
                endpoint, params=page_params, authenticated=authenticated
            )

            if isinstance(data, list):
                all_items.extend(data)
                # Check if there are more pages
                x_pages = headers.get("x-pages", "1")
                if page >= int(x_pages):
                    break
                page += 1
            else:
                # Non-list response, return as-is
                return [data]

        return all_items

    # =========================================================================
    # OAuth Methods
    # =========================================================================

    def get_auth_url(
        self,
        client_id: str,
        redirect_uri: str,
        scopes: list[str],
        state: str | None = None,
    ) -> str:
        """Generate OAuth authorization URL.

        Args:
            client_id: ESI application client ID
            redirect_uri: Callback URL
            scopes: List of ESI scopes to request
            state: Optional state parameter

        Returns:
            Authorization URL to redirect user to
        """
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
        }
        if state:
            params["state"] = state

        return f"{ESI_OAUTH_URL}/authorize?{urlencode(params)}"

    async def exchange_code(
        self,
        code: str,
        client_id: str,
        client_secret: str,
    ) -> TokenData:
        """Exchange authorization code for tokens.

        Args:
            code: Authorization code from callback
            client_id: ESI application client ID
            client_secret: ESI application secret

        Returns:
            Token data with access and refresh tokens
        """
        if not self.client:
            raise RuntimeError("Client not initialized")

        response = await self.client.post(
            f"{ESI_OAUTH_URL}/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
            },
            auth=(client_id, client_secret),
        )
        response.raise_for_status()
        token_data = response.json()

        # Verify and decode token to get character info
        verify_response = await self.client.get(
            f"{ESI_OAUTH_URL}/verify",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        verify_response.raise_for_status()
        verify_data = verify_response.json()

        self._token = TokenData(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_at=datetime.utcnow() + timedelta(seconds=token_data["expires_in"] - 60),
            character_id=verify_data["CharacterID"],
            character_name=verify_data["CharacterName"],
            scopes=verify_data.get("Scopes", "").split(" "),
        )

        return self._token

    async def refresh_token(
        self,
        client_id: str,
        client_secret: str,
    ) -> TokenData:
        """Refresh the access token using refresh token.

        Args:
            client_id: ESI application client ID
            client_secret: ESI application secret

        Returns:
            Updated token data
        """
        if not self._token:
            raise ESIAuthError("No token to refresh")

        if not self.client:
            raise RuntimeError("Client not initialized")

        response = await self.client.post(
            f"{ESI_OAUTH_URL}/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": self._token.refresh_token,
            },
            auth=(client_id, client_secret),
        )
        response.raise_for_status()
        token_data = response.json()

        self._token.access_token = token_data["access_token"]
        self._token.refresh_token = token_data["refresh_token"]
        self._token.expires_at = datetime.utcnow() + timedelta(
            seconds=token_data["expires_in"] - 60
        )

        return self._token

    async def _ensure_token_valid(self) -> None:
        """Ensure the current token is valid, refreshing if needed."""
        if not self._token:
            raise ESIAuthError("No token available")

        if datetime.utcnow() >= self._token.expires_at:
            # Token needs refresh - caller must provide credentials
            raise ESIAuthError("Token expired, refresh required")

    def set_token(self, token: TokenData) -> None:
        """Set the current authentication token."""
        self._token = token

    @property
    def token(self) -> TokenData | None:
        """Get the current token."""
        return self._token

    @property
    def is_authenticated(self) -> bool:
        """Check if client has a valid token."""
        return self._token is not None and datetime.utcnow() < self._token.expires_at
