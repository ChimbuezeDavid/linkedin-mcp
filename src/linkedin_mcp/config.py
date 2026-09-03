"""Configuration settings for LinkedIn MCP server."""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Global configuration settings."""

    # Storage paths
    data_dir: Path = Field(
        default_factory=lambda: Path(
            os.getenv("LINKEDIN_MCP_DATA_DIR", Path.home() / ".linkedin_mcp")
        )
    )

    # Session files
    @property
    def storage_state_file(self) -> Path:
        """Path to Playwright storage state JSON (cookies, local storage)."""
        return self.data_dir / "storage_state.json"

    @property
    def account_identity_file(self) -> Path:
        """Path to cached authenticated account identity info."""
        return self.data_dir / "account_identity.json"

    @property
    def browser_profile_dir(self) -> Path:
        """Persistent browser profile directory."""
        return self.data_dir / "browser_profile"

    # Browser automation settings
    browser_channel: Optional[str] = Field(
        default_factory=lambda: os.getenv("LINKEDIN_BROWSER_CHANNEL", "chrome")
    )
    headless: bool = Field(
        default_factory=lambda: os.getenv("LINKEDIN_HEADLESS", "true").lower()
        in ("1", "true", "yes")
    )
    slow_mo_ms: int = Field(
        default_factory=lambda: int(os.getenv("LINKEDIN_SLOW_MO_MS", "50"))
    )
    timeout_ms: int = Field(
        default_factory=lambda: int(os.getenv("LINKEDIN_TIMEOUT_MS", "30000"))
    )

    # URLs
    base_url: str = "https://www.linkedin.com"
    login_url: str = "https://www.linkedin.com/login"
    feed_url: str = "https://www.linkedin.com/feed/"
    my_profile_url: str = "https://www.linkedin.com/in/me/"

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.browser_profile_dir.mkdir(parents=True, exist_ok=True)


config = Settings()
config.ensure_directories()
