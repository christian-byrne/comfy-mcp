"""Configuration for template synchronization."""

from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
import os


@dataclass
class SyncConfig:
    """Configuration for template synchronization."""
    
    # GitHub repository settings
    github_repo: str = "Comfy-Org/workflow_templates"
    github_branch: str = "main"
    templates_path: str = "templates"
    
    # Rate limiting and retry settings
    max_concurrent_downloads: int = 5
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Template filtering
    exclude_patterns: List[str] = None
    include_patterns: List[str] = None
    min_file_size: int = 100  # Minimum file size in bytes
    max_file_size: int = 10 * 1024 * 1024  # Maximum file size in bytes (10MB)
    
    # DSL conversion settings
    skip_conversion_errors: bool = True  # Continue sync even if some conversions fail
    save_failed_conversions: bool = True  # Save templates even if DSL conversion fails
    
    # Cache settings
    cache_dir: Optional[Path] = None
    cache_ttl_hours: int = 24  # How long cache is valid
    backup_cache: bool = True  # Keep backup of previous cache
    
    # Notification settings
    notify_on_sync: bool = False
    notify_on_errors: bool = True
    notification_threshold: int = 10  # Minimum templates to notify about
    
    def __post_init__(self):
        """Initialize default values that depend on runtime."""
        if self.exclude_patterns is None:
            self.exclude_patterns = [
                "*.tmp",
                "*.temp", 
                "*test*",
                "*example*",
                "*deprecated*"
            ]
        
        if self.include_patterns is None:
            self.include_patterns = ["*.json"]
        
        if self.cache_dir is None:
            self.cache_dir = Path.cwd() / ".template_cache"
    
    @classmethod
    def from_env(cls) -> "SyncConfig":
        """Create configuration from environment variables."""
        return cls(
            github_repo=os.getenv("SYNC_GITHUB_REPO", "Comfy-Org/workflow_templates"),
            github_branch=os.getenv("SYNC_GITHUB_BRANCH", "main"),
            templates_path=os.getenv("SYNC_TEMPLATES_PATH", "templates"),
            max_concurrent_downloads=int(os.getenv("SYNC_MAX_CONCURRENT", "5")),
            request_timeout=int(os.getenv("SYNC_REQUEST_TIMEOUT", "30")),
            max_retries=int(os.getenv("SYNC_MAX_RETRIES", "3")),
            skip_conversion_errors=os.getenv("SYNC_SKIP_ERRORS", "true").lower() == "true",
            cache_ttl_hours=int(os.getenv("SYNC_CACHE_TTL", "24")),
            notify_on_sync=os.getenv("SYNC_NOTIFY", "false").lower() == "true",
            notification_threshold=int(os.getenv("SYNC_NOTIFY_THRESHOLD", "10"))
        )
    
    def should_sync_template(self, filename: str, file_size: int) -> bool:
        """Check if a template should be synced based on filters."""
        # Check file size
        if file_size < self.min_file_size or file_size > self.max_file_size:
            return False
        
        # Check include patterns
        if self.include_patterns:
            if not any(self._matches_pattern(filename, pattern) for pattern in self.include_patterns):
                return False
        
        # Check exclude patterns
        if self.exclude_patterns:
            if any(self._matches_pattern(filename, pattern) for pattern in self.exclude_patterns):
                return False
        
        return True
    
    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if filename matches a pattern (supports basic wildcards)."""
        import fnmatch
        return fnmatch.fnmatch(filename.lower(), pattern.lower())


# Default configuration instance
DEFAULT_SYNC_CONFIG = SyncConfig()


def get_sync_config() -> SyncConfig:
    """Get the current sync configuration."""
    # Check if we're in CI environment
    if os.getenv("GITHUB_ACTIONS") == "true":
        return SyncConfig.from_env()
    
    return DEFAULT_SYNC_CONFIG