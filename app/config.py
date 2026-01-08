"""Configuration management using Pydantic Settings.

This module provides type-safe configuration with validation,
loading settings from environment variables and .env files.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class GitHubAppSettings(BaseSettings):
    """GitHub App configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="GITHUB_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_id: int = Field(
        ...,
        description="GitHub App ID from app settings page",
        examples=[123456],
    )
    private_key_path: Path = Field(
        ...,
        description="Path to GitHub App private key file (.pem)",
        examples=["./private-key.pem"],
    )
    webhook_secret: str = Field(
        ...,
        description="Secret for verifying GitHub webhook signatures",
        min_length=16,
    )
    installation_id: Optional[int] = Field(
        default=None,
        description="GitHub App installation ID (optional, auto-detected if not set)",
    )

    @field_validator("private_key_path", mode="before")
    @classmethod
    def validate_private_key_path(cls, v) -> Path:
        """Validate that the private key file exists.
        
        Resolves relative paths from the project root directory.
        """
        # Convert to Path if it's a string
        if isinstance(v, str):
            path = Path(v)
        else:
            path = Path(v)
        
        # If path is relative, resolve it from the project root
        if not path.is_absolute():
            # Get the project root (parent of app directory)
            project_root = Path(__file__).parent.parent
            path = (project_root / path).resolve()
        
        # Validate file exists
        if not path.exists():
            raise ValueError(
                f"Private key file not found: {path}\n"
                f"Please ensure the file exists at this path, or set GITHUB_PRIVATE_KEY_PATH "
                f"to the correct path relative to the project root (e.g., './private-key.pem')."
            )
        if not path.is_file():
            raise ValueError(f"Private key path is not a file: {path}")
        return path

    @property
    def private_key(self) -> str:
        """Read and return the GitHub private key from file."""
        return self.private_key_path.read_text(encoding="utf-8")


class GeminiAPISettings(BaseSettings):
    """Google Gemini API configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="GEMINI_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    api_key: str = Field(
        ...,
        description="Google Gemini API key from AI Studio",
        min_length=20,
    )
    model_name: str = Field(
        default="gemini-2.5-flash-lite",
        description="Gemini model to use for code review",
        examples=["gemini-2.5-flash-lite", "gemini-1.5-pro-latest"],
    )
    temperature: float = Field(
        default=0.2,
        description="Model temperature for response randomness (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    max_tokens: int = Field(
        default=8192,
        description="Maximum tokens in model response",
        gt=0,
        le=32768,
    )

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key format."""
        if not v.startswith("AIza"):
            raise ValueError("Invalid Gemini API key format")
        return v


class JIRASettings(BaseSettings):
    """JIRA integration configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="JIRA_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    base_url: Optional[str] = Field(
        default=None,
        description="JIRA instance base URL",
        examples=["https://your-domain.atlassian.net"],
    )
    email: Optional[str] = Field(
        default=None,
        description="JIRA account email address",
    )
    api_token: Optional[str] = Field(
        default=None,
        description="JIRA API token for authentication",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate JIRA base URL format."""
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("JIRA base URL must start with http:// or https://")
        return v

    @property
    def enabled(self) -> bool:
        """Check if JIRA integration is properly configured."""
        return all([self.base_url, self.email, self.api_token])


class ServerSettings(BaseSettings):
    """Server configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    host: str = Field(
        default="0.0.0.0",
        description="Server bind address",
    )
    port: int = Field(
        default=8000,
        description="Server port number",
        gt=0,
        lt=65536,
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode (development only)",
    )
    log_level: str = Field(
        default="info",
        description="Logging level",
        pattern="^(debug|info|warning|error|critical)$",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Normalize log level to uppercase."""
        return v.upper()


class FeaturesSettings(BaseSettings):
    """Feature flags and configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    enable_caching: bool = Field(
        default=True,
        description="Enable response caching for improved performance",
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        description="Cache time-to-live in seconds (1 hour default)",
        gt=0,
    )
    rate_limit_per_hour: int = Field(
        default=100,
        description="Maximum API requests per hour per repository",
        gt=0,
    )
    max_files_per_review: int = Field(
        default=50,
        description="Maximum number of files to review per PR",
        gt=0,
    )
    review_timeout_seconds: int = Field(
        default=300,
        description="Maximum time for review process in seconds (5 minutes)",
        gt=0,
    )


class Settings(BaseSettings):
    """Main application settings combining all configuration groups.

    This class aggregates all configuration settings and provides
    a single point of access for the entire application configuration.

    Settings are loaded from:
    1. Environment variables
    2. .env file in the project root
    3. Default values defined in each settings group

    Example:
        ```python
        from app.config import get_settings

        settings = get_settings()
        print(settings.github.app_id)
        print(settings.gemini.model_name)
        print(settings.server.port)
        ```
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Nested configuration groups
    github: GitHubAppSettings = Field(default_factory=GitHubAppSettings)
    gemini: GeminiAPISettings = Field(default_factory=GeminiAPISettings)
    jira: JIRASettings = Field(default_factory=JIRASettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    features: FeaturesSettings = Field(default_factory=FeaturesSettings)

    # Application metadata
    app_name: str = Field(
        default="RepoAuditor AI",
        description="Application name",
    )
    app_version: str = Field(
        default="1.0.0",
        description="Application version",
    )

    @property
    def is_debug(self) -> bool:
        """Shortcut to check if debug mode is enabled."""
        return self.server.debug

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.server.debug and self.server.log_level in ("info", "warning", "error", "critical")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    This function returns a cached singleton instance of Settings.
    The settings are loaded once and reused throughout the application
    lifecycle for better performance.

    Returns:
        Settings: Configured application settings

    Example:
        ```python
        from app.config import get_settings

        settings = get_settings()
        print(f"GitHub App ID: {settings.github.app_id}")
        print(f"Using Gemini model: {settings.gemini.model_name}")
        print(f"JIRA enabled: {settings.jira.enabled}")
        ```
    """
    return Settings()


# Convenience: Export settings instance for backward compatibility
settings = get_settings()
