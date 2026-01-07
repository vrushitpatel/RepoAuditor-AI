"""Configuration management using Pydantic settings."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # GitHub App Configuration
    github_app_id: int = Field(..., description="GitHub App ID")
    github_private_key_path: Path = Field(..., description="Path to GitHub App private key")
    github_webhook_secret: str = Field(..., description="GitHub webhook secret for verification")

    # Gemini AI Configuration
    gemini_api_key: str = Field(..., description="Google Gemini API key")
    gemini_model: str = Field(default="gemini-2.0-flash-exp", description="Gemini model to use")

    # Jira Configuration (Optional)
    jira_base_url: Optional[str] = Field(default=None, description="Jira instance base URL")
    jira_email: Optional[str] = Field(default=None, description="Jira account email")
    jira_api_token: Optional[str] = Field(default=None, description="Jira API token")

    # Application Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")

    # Review Configuration
    max_files_per_review: int = Field(default=50, description="Maximum files to review per PR")
    review_timeout_seconds: int = Field(default=300, description="Maximum time for review process")

    @property
    def github_private_key(self) -> str:
        """Read and return the GitHub private key from file."""
        return self.github_private_key_path.read_text(encoding="utf-8")

    @property
    def jira_enabled(self) -> bool:
        """Check if Jira integration is enabled."""
        return all([self.jira_base_url, self.jira_email, self.jira_api_token])


# Global settings instance
settings = Settings()
