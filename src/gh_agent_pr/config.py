"""Configuration loading for gh-agent-pr."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import yaml


@dataclass
class Config:
    repos: List[str] = field(default_factory=list)
    limit: int = 20
    laya_model: str = "english"
    max_tokens: int = 4096
    interactive: bool = False


def load_config(
    config_path: Optional[str] = None,
    cli_repos: Optional[List[str]] = None,
    limit: Optional[int] = None,
    laya_model: Optional[str] = None,
    interactive: Optional[bool] = None,
) -> Config:
    """Load configuration from file and/or CLI arguments.
    
    CLI arguments take precedence over config file values.
    """
    data = {}
    candidate_paths = []
    if config_path:
        candidate_paths.append(Path(config_path))
    else:
        candidate_paths.extend([
            Path("gh-agent-pr.yaml"),
            Path("gh-agent-pr.yml"),
            Path.home() / ".config" / "gh-agent-pr" / "config.yaml",
        ])

    for path in candidate_paths:
        if path.is_file():
            with open(path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    data = loaded
            break

    repos = []
    if cli_repos:
        repos = [r.strip() for r in cli_repos if r.strip()]
    elif "repos" in data and isinstance(data["repos"], list):
        repos = [str(r).strip() for r in data["repos"] if str(r).strip()]

    conf_limit = limit if limit is not None else data.get("limit", 20)
    conf_model = laya_model if laya_model is not None else data.get("laya_model", "english")
    conf_max_tokens = data.get("max_tokens", 4096)
    conf_interactive = interactive if interactive is not None else bool(data.get("interactive", False))

    return Config(
        repos=repos,
        limit=conf_limit,
        laya_model=conf_model,
        max_tokens=conf_max_tokens,
        interactive=conf_interactive,
    )
