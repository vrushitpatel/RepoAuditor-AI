"""GitHub App authentication using JWT and installation tokens."""

import time
from datetime import datetime, timedelta
from typing import Dict, Optional

import jwt
from github import GithubIntegration

from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class GitHubAuth:
    """
    Handles GitHub App authentication with JWT generation and token management.

    This class manages:
    - JWT generation for GitHub App authentication
    - Installation access token retrieval and caching
    - Automatic token refresh when expired

    Example:
        ```python
        auth = GitHubAuth()
        token = auth.get_installation_token(installation_id=12345)
        # Use token for API requests
        ```
    """

    def __init__(self) -> None:
        """Initialize GitHub authentication with app credentials."""
        self.app_id = settings.github.app_id
        self.private_key = settings.github.private_key
        self._integration: Optional[GithubIntegration] = None
        self._token_cache: Dict[int, Dict[str, any]] = {}

    def generate_jwt(self, expiration_seconds: int = 600) -> str:
        """
        Generate a JSON Web Token (JWT) for GitHub App authentication.

        The JWT is used to authenticate as the GitHub App itself (not as an installation).
        It's required to get installation access tokens.

        Args:
            expiration_seconds: JWT expiration time in seconds (max 600, default 600)

        Returns:
            JWT token as string

        Raises:
            ValueError: If expiration_seconds is greater than 600

        Example:
            ```python
            auth = GitHubAuth()
            jwt_token = auth.generate_jwt()
            # Use jwt_token in Authorization header: "Bearer <jwt_token>"
            ```

        Note:
            GitHub requires JWT expiration to be maximum 10 minutes (600 seconds).
        """
        if expiration_seconds > 600:
            raise ValueError("JWT expiration cannot exceed 600 seconds (10 minutes)")

        # Current time
        now = int(time.time())

        # JWT payload
        payload = {
            # Issued at time
            "iat": now,
            # JWT expiration time (10 minutes maximum)
            "exp": now + expiration_seconds,
            # GitHub App's identifier
            "iss": self.app_id,
        }

        # Create JWT
        encoded_jwt = jwt.encode(
            payload,
            self.private_key,
            algorithm="RS256",
        )

        logger.debug(
            f"Generated JWT for GitHub App {self.app_id}",
            extra={
                "extra_fields": {
                    "app_id": self.app_id,
                    "expires_in": expiration_seconds,
                }
            },
        )

        return encoded_jwt

    def _get_integration(self) -> GithubIntegration:
        """
        Get or create GitHub integration instance.

        Returns:
            GithubIntegration instance

        Note:
            This is cached to avoid recreating the integration object.
        """
        if self._integration is None:
            self._integration = GithubIntegration(
                self.app_id,
                self.private_key,
            )
            logger.debug("Created GitHub integration instance")

        return self._integration

    def get_installation_token(
        self,
        installation_id: int,
        force_refresh: bool = False,
    ) -> str:
        """
        Get installation access token with automatic caching and refresh.

        Installation access tokens are used to authenticate API requests
        on behalf of a specific installation. These tokens expire after 1 hour.

        Args:
            installation_id: GitHub App installation ID
            force_refresh: Force token refresh even if cached token is valid

        Returns:
            Installation access token as string

        Example:
            ```python
            auth = GitHubAuth()
            token = auth.get_installation_token(installation_id=12345)

            # Use token for API requests
            headers = {"Authorization": f"token {token}"}
            response = requests.get(api_url, headers=headers)
            ```

        Note:
            Tokens are cached and automatically refreshed when expired.
        """
        # Check if we have a valid cached token
        if not force_refresh and installation_id in self._token_cache:
            cached = self._token_cache[installation_id]
            if cached["expires_at"] > datetime.utcnow():
                logger.debug(
                    f"Using cached token for installation {installation_id}",
                    extra={
                        "extra_fields": {
                            "installation_id": installation_id,
                            "expires_at": cached["expires_at"].isoformat(),
                        }
                    },
                )
                return cached["token"]

        # Get new token
        integration = self._get_integration()
        access_token = integration.get_access_token(installation_id)

        # Cache the token (tokens expire after 1 hour)
        # We refresh 5 minutes early to be safe
        expires_at = datetime.utcnow() + timedelta(minutes=55)
        self._token_cache[installation_id] = {
            "token": access_token.token,
            "expires_at": expires_at,
        }

        logger.info(
            f"Retrieved new installation token for installation {installation_id}",
            extra={
                "extra_fields": {
                    "installation_id": installation_id,
                    "expires_at": expires_at.isoformat(),
                }
            },
        )

        return access_token.token

    def invalidate_token(self, installation_id: int) -> None:
        """
        Invalidate cached token for an installation.

        Forces a token refresh on next get_installation_token call.

        Args:
            installation_id: GitHub App installation ID

        Example:
            ```python
            auth = GitHubAuth()
            # If you get a 401 error, invalidate and retry
            auth.invalidate_token(installation_id)
            new_token = auth.get_installation_token(installation_id)
            ```
        """
        if installation_id in self._token_cache:
            del self._token_cache[installation_id]
            logger.info(f"Invalidated token for installation {installation_id}")

    def clear_all_tokens(self) -> None:
        """
        Clear all cached tokens.

        Useful for testing or if you want to force refresh all tokens.

        Example:
            ```python
            auth = GitHubAuth()
            auth.clear_all_tokens()
            ```
        """
        count = len(self._token_cache)
        self._token_cache.clear()
        logger.info(f"Cleared {count} cached tokens")

    def get_token_expiration(self, installation_id: int) -> Optional[datetime]:
        """
        Get expiration time for cached token.

        Args:
            installation_id: GitHub App installation ID

        Returns:
            Expiration datetime if token is cached, None otherwise

        Example:
            ```python
            auth = GitHubAuth()
            expires_at = auth.get_token_expiration(installation_id)
            if expires_at:
                print(f"Token expires at: {expires_at}")
            ```
        """
        if installation_id in self._token_cache:
            return self._token_cache[installation_id]["expires_at"]
        return None

    def is_token_valid(self, installation_id: int) -> bool:
        """
        Check if cached token is still valid.

        Args:
            installation_id: GitHub App installation ID

        Returns:
            True if token exists and is not expired, False otherwise

        Example:
            ```python
            auth = GitHubAuth()
            if not auth.is_token_valid(installation_id):
                # Get new token
                token = auth.get_installation_token(installation_id)
            ```
        """
        if installation_id not in self._token_cache:
            return False

        expires_at = self._token_cache[installation_id]["expires_at"]
        is_valid = expires_at > datetime.utcnow()

        logger.debug(
            f"Token validation for installation {installation_id}: {is_valid}",
            extra={
                "extra_fields": {
                    "installation_id": installation_id,
                    "is_valid": is_valid,
                    "expires_at": expires_at.isoformat() if expires_at else None,
                }
            },
        )

        return is_valid
